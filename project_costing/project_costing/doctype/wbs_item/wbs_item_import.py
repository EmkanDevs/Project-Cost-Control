import frappe
import pandas as pd
import re
from frappe.utils import now_datetime

# Optimized WBS import: batch-friendly, cached lookups, single commit, reduced realtime
# Usage:
#   import_wbs_from_file_fast(file_name, boq_name, project_name, warehouse)
# If file_name is a local path (e.g. /mnt/data/...), it will be used directly.

@frappe.whitelist()
def import_wbs_from_file_fast(file_name, boq_name, project_name, warehouse, progress_interval=20):
    """Fast import for WBS items.

    Key optimizations:
    - No per-row commits (single commit at end)
    - Cached get_value lookups
    - Reduced publish_realtime frequency
    - Avoid get_doc in hot loops
    - Bulk mark groups at end
    """

    if not file_name:
        frappe.throw("No file provided.")

    # Support direct local path uploads (developer helper)
    if file_name.startswith("/mnt/"):
        file_path = file_name
    else:
        file_doc = frappe.get_doc("File", {"file_url": file_name})
        file_path = file_doc.get_full_path()

    try:
        if file_path.lower().endswith('.csv'):
            df = pd.read_csv(file_path, header=0)
        else:
            df = pd.read_excel(file_path, header=0)
    except Exception as e:
        frappe.throw(f"Error reading file {file_name}: {e}. Ensure valid CSV/Excel.")

    if df.empty:
        frappe.throw("The uploaded file is empty.")

    df.columns = df.columns.str.strip()

    # Detect columns
    wbs_col = next((c for c in df.columns if 'cost code' in c.lower() or 'wbs' in c.lower()), None)
    level_col = next((c for c in df.columns if 'level' in c.lower()), None)
    boq_id_col = next((c for c in df.columns if 'boq id' in c.lower()), None)
    res_type_col = next((c for c in df.columns if 'res' in c.lower() and 'type' in c.lower()), None)

    if not wbs_col:
        frappe.throw("WBS Code column not found. Please ensure your file has a 'Cost Code' or 'WBS' column.")
    if not level_col:
        frappe.throw("Level column not found. Please ensure your file has a 'Level' column.")

    rename_dict = {wbs_col: 'wbs_code', level_col: 'level'}
    if boq_id_col:
        rename_dict[boq_id_col] = 'boq_id'
    if res_type_col:
        rename_dict[res_type_col] = 'res_type'

    df = df.rename(columns=rename_dict)

    # Clean
    df.dropna(subset=['wbs_code'], inplace=True)
    df['wbs_code'] = df['wbs_code'].astype(str).str.strip()
    df = df[~df['wbs_code'].str.lower().isin(['nan', ''])]

    df['level'] = pd.to_numeric(df['level'], errors='coerce')
    df = df.dropna(subset=['level'])
    df['level'] = df['level'].astype(int)

    df['res_type'] = df.get('res_type', pd.NA).apply(lambda v: v.strip() if isinstance(v, str) else v)
    df.loc[df['res_type'] == '', 'res_type'] = pd.NA

    df = df.reset_index(drop=True)
    if df.empty:
        frappe.throw("File contains no rows with valid WBS Codes after cleaning.")

    total = len(df)

    # Project detection (from first code) - keep existing behavior but cache results
    first_code = df.iloc[0]['wbs_code']
    m = re.match(r"([A-Z]+)(\d{2})", first_code)
    project = None
    if m:
        project_abbr, start_year = m.group(1), m.group(2)
        project = frappe.get_value("Project", {
            "custom_project_abbr": project_abbr,
            "custom_start_year": ["in", [start_year, int(start_year)]],
        }, "name")
    if not project:
        # fallback to provided project_name if given
        project = project_name
    if not project:
        frappe.throw(f"No Project found for abbreviation in '{first_code}'. Provide project_name or correct code.")

    # Cache metadata and valid fields
    meta = frappe.get_meta('WBS item')
    valid_fields = {f.fieldname for f in meta.fields}

    # Column mapping (only use if present)
    column_map = {
        'BOQ Qty': 'qty',
        'Resource QTY': 'resource_qty',
        'Waste ratio': 'waste',
        'Total Resource QTY': 'custom_total_resource_qty',
        'Material Rate': 'unit_cost',
        'Budget Rate': 'unit_rate',
        'BOQ ID': 'boq_id',
        'Finance Code': 'cost_center_code',
        'Item Description': 'short_description',
        'Combined Code': 'combined_code',
        'Item': 'item_code',
        'Res. Type': 'res_type',
        'Unit': 'uom'
    }

    # Prefetch existing WBS items for this BOQ to help parent lookup
    existing_wbs = frappe.get_all('WBS item', filters={'boq': boq_name}, fields=['name', 'cost_code', 'level', 'parent_wbs_item'])
    existing_map = {r['cost_code']: r for r in existing_wbs}

    # Caches to reduce DB hits
    item_cache = {}
    cost_center_cache = {}
    boq_details_cache = {}

    inserted = []
    failed = []
    success = 0

    # We'll build an in-memory mapping of code -> name for inserted docs as we go
    wbs_code_to_name = {k: v['name'] for k, v in existing_map.items()}

    # Helper functions
    def get_cost_center(abbr):
        if not abbr:
            return None
        if abbr in cost_center_cache:
            return cost_center_cache[abbr]
        cc = frappe.get_value('Cost Center', {'custom_abbr': abbr}, 'name')
        cost_center_cache[abbr] = cc
        return cc

    def get_boq_details(boq_id):
        if not boq_id:
            return None
        if boq_id in boq_details_cache:
            return boq_details_cache[boq_id]
        val = frappe.get_value('BOQ Details', {'boq_id': boq_id}, 'name')
        boq_details_cache[boq_id] = val
        return val

    def get_item_by_code(code):
        if not code:
            return None
        if code in item_cache:
            return item_cache[code]
        val = frappe.get_value('Item', {'item_code': code}, 'name')
        item_cache[code] = val
        return val

    # Process rows
    for idx, row in df.iterrows():
        code = row['wbs_code']
        excel_level = int(row['level'])
        res_type = row.get('res_type') if 'res_type' in row else None

        if not code or pd.isna(code):
            failed.append(f"Row {idx+2}: Missing Cost Code")
            continue

        try:
            # Prepare doc
            doc = frappe.new_doc('WBS item')
            doc.cost_code = code

            # Map levels >4 to 4 (same logic as original)
            mapped_level = excel_level if excel_level <= 4 else 4
            doc.level = mapped_level

            doc.boq = boq_name
            doc.project = project
            doc.warehouse = warehouse

            has_resource_type = res_type and pd.notna(res_type) and str(res_type).strip() != ''
            is_item_like = (excel_level >= 5) or has_resource_type
            doc.is_group = 0 if is_item_like else 1

            # Efficient parent resolution:
            parent_name = None

            if mapped_level > 1:
                # Primary: try direct prefix split (common pattern: ABC-01-02)
                parts = code.split('-')
                if len(parts) > 1:
                    parent_code = '-'.join(parts[:-1])
                    parent_name = wbs_code_to_name.get(parent_code)

                # Secondary: try full scan of in-memory map for matching prefix and level-1
                if not parent_name:
                    # prefer exact match of parent by checking codes whose level == mapped_level-1
                    for existing_code, existing_name in wbs_code_to_name.items():
                        # quick filter: must be shorter and be a prefix
                        if len(existing_code) < len(code) and code.startswith(existing_code) and existing_map.get(existing_code, {}).get('level') == mapped_level - 1:
                            parent_name = existing_name
                            break

            if parent_name:
                doc.parent_wbs_item = parent_name

            # cost center for level 2
            if doc.level == 2:
                seg = "-".join(code.split("-")[1:])
                cc = get_cost_center(seg)
                if cc:
                    doc.cost_center = cc

            # link BOQ details
            boq_id_val = None
            if 'BOQ ID' in df.columns:
                boq_id_val = row.get('BOQ ID')
            elif 'boq_id' in row.index:
                boq_id_val = row.get('boq_id')

            if pd.notna(boq_id_val) and str(boq_id_val).strip() != '':
                boq_det = get_boq_details(str(boq_id_val).strip())
                if boq_det and 'boq_details' in valid_fields:
                    doc.boq_details = boq_det

            # item-specific handling
            if is_item_like:
                item_code_from_excel = row.get('Item') if 'Item' in df.columns else None
                if pd.notna(item_code_from_excel) and str(item_code_from_excel).strip() != '':
                    truncated_item_code = str(item_code_from_excel)[:140]
                    if 'item_code' in valid_fields:
                        doc.item_code = truncated_item_code
                        existing_item = get_item_by_code(truncated_item_code)
                        if existing_item:
                            doc.item = existing_item

                desc = None
                if 'Item Description' in df.columns:
                    desc = row.get('Item Description')
                if pd.notna(desc) and str(desc).strip() != '':
                    doc.short_description = str(desc).strip()

            # UOM
            if 'Unit' in df.columns:
                uom = row.get('Unit')
                if pd.notna(uom) and str(uom).strip() != '':
                    doc.uom = str(uom).strip()

            # Map other columns - minimal parsing
            for col, fld in column_map.items():
                if col not in df.columns:
                    continue
                if fld == 'res_type':
                    continue
                # skip if already handled
                if is_item_like and col in ['Item', 'Item Description']:
                    continue

                val = row.get(col)
                if pd.isna(val) or str(val).strip() == '':
                    continue

                if fld in ['qty', 'resource_qty', 'waste', 'custom_total_resource_qty', 'unit_cost', 'unit_rate']:
                    try:
                        numeric_val = float(str(val).strip())
                        if fld in valid_fields:
                            doc.set(fld, numeric_val)
                    except Exception:
                        # skip invalid numeric
                        pass
                else:
                    if fld in valid_fields:
                        doc.set(fld, str(val).strip())

            # Insert without committing on every row to save IO
            doc.insert(ignore_permissions=True)

            # Keep maps updated
            wbs_code_to_name[code] = doc.name
            # also update existing_map in-memory so later checks can use level info
            existing_map[code] = {'name': doc.name, 'level': doc.level}

            inserted.append({'cost_code': doc.cost_code, 'name': doc.name, 'level': doc.level})
            success += 1

            # Progress pub every `progress_interval` rows
            if (idx + 1) % progress_interval == 0 or (idx + 1) == total:
                progress = int(((idx + 1) / total) * 100)
                try:
                    frappe.publish_realtime('import_progress', {
                        'status': f'Processing row {idx+1}/{total} - {code}',
                        'progress': progress
                    })
                except Exception:
                    # non-fatal if realtime fails
                    pass

        except Exception as e:
            frappe.log_error(title=f'WBS Import Error Row {idx+2}', message=str(e)[:1000])
            failed.append(f"Row {idx+2}: Error inserting {code} -> {str(e)}")
            # rollback only the doc insertion in memory; do not rollback entire transaction here
            frappe.db.rollback()

    # Single commit at end
    try:
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(title='WBS Import Final Commit Error', message=str(e)[:2000])
        # If final commit fails, raise so user knows
        frappe.throw(f"Failed to commit imported WBS items: {e}")

    # Update BOQ flag once
    try:
        frappe.db.set_value('BOQ', boq_name, 'wbs_item_created', 1)
        frappe.db.commit()
    except Exception as e:
        # non-fatal
        frappe.msgprint(f"Warning: Could not update BOQ flag: {e}")

    # Mark groups (use existing optimized function)
    try:
        mark_wbs_groups_as_is_group(boq_name)
    except Exception:
        pass

    # Summary msg
    frappe.msgprint(f"Import finished. Total: {total}, Success: {success}, Failed: {len(failed)}")

    return {"total": total, "success": success, "failed": failed, "inserted": inserted}


@frappe.whitelist()
def import_wbs_from_file_async(file_name, boq_name, project_name, warehouse):
    """Enqueue the optimized import with a long timeout."""
    job = frappe.enqueue(
        'project_costing.project_costing.doctype.wbs_item.wbs_item_import.import_wbs_from_file_fast',
        file_name=file_name,
        boq_name=boq_name,
        project_name=project_name,
        warehouse=warehouse,
        queue='long',
        timeout=7200
    )
    return {'job_id': job.id}


# Helper remains the same as earlier but slightly optimized
def mark_wbs_groups_as_is_group(boq_name):
    try:
        child_parents = frappe.get_all(
            'WBS item',
            filters={'boq': boq_name, 'parent_wbs_item': ['!=', '']},
            fields=['parent_wbs_item']
        )
        parent_names = set(c['parent_wbs_item'] for c in child_parents)
        if parent_names:
            for parent_name in parent_names:
                frappe.db.set_value('WBS item', parent_name, 'is_group', 1)
            frappe.db.commit()
    except Exception as e:
        frappe.msgprint(f"Warning: Could not mark WBS groups: {e}")
