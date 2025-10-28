import frappe
import pandas as pd
import re
from frappe.utils import now_datetime

def normalize_cost_code(raw_code):
    raw_code = raw_code.replace('ASF-', 'ASF').upper()
    parts = raw_code.split('-')
    normalized_parts = []
    for idx, part in enumerate(parts):
        if idx == 2:
            normalized_parts.append(part)
        else:
            if part.isdigit():
                normalized_parts.append(str(int(part)))
            else:
                match = re.match(r'([A-Z]+)(\d+)', part, re.I)
                if match:
                    prefix, number = match.groups()
                    normalized_parts.append(f"{prefix.upper()}{int(number)}")
                else:
                    normalized_parts.append(part)
    return '-'.join(normalized_parts)

@frappe.whitelist()
def import_wbs_from_file(file_name, boq_name, project_name, warehouse):
    if not file_name:
        frappe.throw("No file provided.")

    file_doc = frappe.get_doc("File", {"file_url": file_name})
    file_path = file_doc.get_full_path()

    try:
        if file_path.lower().endswith('.csv'):
            df = pd.read_csv(file_path, header=0)
        else:
            df = pd.read_excel(file_path, header=0)
    except Exception as e:
        frappe.throw(f"Error reading file {file_name}: {e}. Please ensure it's a valid CSV or Excel file and not corrupted.")

    if df.empty:
        frappe.throw("The uploaded file is empty or contains no data after skipping the header row (row 1).")

    df.columns = df.columns.str.strip()

    wbs_col = next((c for c in df.columns if 'cost code' in c.lower()), None)
    if not wbs_col:
        frappe.throw("WBS Code column not found. Please ensure your file has a 'Cost Code' column.")
    df = df.rename(columns={wbs_col: "wbs_code"})

    df.dropna(subset=['wbs_code'], inplace=True)
    df['wbs_code'] = df['wbs_code'].astype(str).str.strip()
    df = df[~df['wbs_code'].str.lower().isin(['nan', ''])]
    df.reset_index(drop=True, inplace=True)

    if df.empty:
        frappe.throw("File contains no rows with valid WBS Codes after cleaning.")

    res_cols = [c for c in df.columns if 'res' in c.lower() and 'type' in c.lower()]
    if not res_cols:
        frappe.throw("Res. Type column not found. Available columns: " + ", ".join(df.columns))
    res_col = res_cols[0]
    df = df.rename(columns={res_col: "res_type"})
    df['res_type'] = df['res_type'].apply(lambda v: v.strip() if isinstance(v, str) else v)
    df.loc[df['res_type'] == '', 'res_type'] = pd.NA

    first_code = df.iloc[0]['wbs_code']
    m = re.match(r"([A-Z]+)(\d{2})", first_code)
    if not m:
        frappe.throw(f"Invalid Cost Code format: {first_code}. Expected format like 'ABC00'.")
    project_abbr, start_year = m.group(1), m.group(2)
    project = frappe.get_value("Project", {
        "custom_project_abbr": project_abbr,
        "custom_start_year": ["in", [start_year, int(start_year)]],
    }, "name")
    if not project:
        frappe.throw(f"No Project found for abbreviation '{project_abbr}' and start year '{start_year}'.")

    def lvl_parent(code, res_type):
        parts = code.split('-')
        n = len(parts)
        if n == 1:
            return 1, None
        elif n == 2:
            return 2, parts[0]
        elif n == 3:
            return 2, parts[0]
        elif n == 4:
            return 3, '-'.join(parts[:3])
        elif n == 5:
            return 4, '-'.join(parts[:4])
        return None, None

    df[['level', 'parent_code']] = df.apply(lambda row: pd.Series(lvl_parent(row['wbs_code'], row['res_type'])), axis=1)

    df = df.sort_values(by=['level', 'wbs_code']).reset_index(drop=True)

    meta = frappe.get_meta("WBS item")
    valid_fields = {f.fieldname for f in meta.fields}
    column_map = {
        "BOQ Qty": "qty",
        "Resource QTY": "resource_qty",
        "Waste": "waste",
        "Total Resource QTY": "custom_total_resource_qty",
        "Material Rate": "unit_cost",
        "Budget Rate": "unit_rate",
        "BOQ ID": "boq_id",
        "Finance Code": "cost_center_code",
        "Item Description": "short_description",
        "Combined Code": "combined_code",
        "Item": "item_code",
        "Res. Type": "res_type",
        "Unit": "uom"
    }

    inserted = {}
    inserted_docs = []
    success, failed, total = 0, [], len(df)
    all_codes = set(df['wbs_code'])

    for idx, row in df.iterrows():
        code, lvl, parent, res_type = row['wbs_code'], row['level'], row['parent_code'], row['res_type']

        if not code or pd.isna(code):
            failed.append(f"Row {idx+2}: Skipped due to missing Cost Code")
            continue

        if pd.isna(lvl):
            failed.append(f"Row {idx+2}: Skipped {code} (invalid or missing level: {lvl})")
            continue

        doc = frappe.new_doc("WBS item")
        doc.cost_code = code
        doc.level = int(lvl)
        doc.boq = boq_name
        doc.project = project_name
        doc.warehouse = warehouse
        doc.uom = row.get("Unit")
        doc.item_code = row.get("Item")
        doc.short_description = row.get("Item Description")

        is_item_like_wbs = (len(code.split('-')) == 5)
        doc.is_group = 0 if is_item_like_wbs else 1

        # ------------------ Parent WBS Logic --------------------
        
        parent_wbs = None
        if lvl > 1:
            if parent in inserted:
                parent_wbs = inserted[parent]
            else:
                if parent in all_codes:
                    failed.append(f"Row {idx+2}: {code} (Parent {parent} exists in file but not yet inserted)")
                    continue
                else:
                    # Fallback to nearest existing ancestor
                    ancestor = parent
                    while ancestor:
                        ancestor = '-'.join(ancestor.split('-')[:-1])
                        if ancestor in inserted:
                            parent_wbs = inserted[ancestor]
                            frappe.msgprint(f"[Fallback] Using nearest ancestor '{ancestor}' as parent for '{code}'")
                            break
                    if not parent_wbs:
                        try:
                            parent_doc = frappe.new_doc("WBS item")
                            parent_doc.cost_code = parent
                            parent_doc.level = lvl - 1
                            parent_doc.boq = boq_name
                            parent_doc.project = project_name
                            parent_doc.is_group = 1
                            parent_doc.insert()
                            frappe.db.commit()
                            inserted[parent] = parent_doc.name
                            parent_wbs = parent_doc.name
                            frappe.msgprint(f"[Auto-create] Inserted missing parent '{parent}' for '{code}'")
                        except Exception as e:
                            failed.append(f"Row {idx+2}: {code} (Auto-create parent '{parent}' failed: {e})")
                            frappe.db.rollback()
                            continue
            doc.parent_wbs_item = parent_wbs

        if lvl == 2:
            seg = "-".join(code.split("-")[1:])
            cc = frappe.get_value("Cost Center", {"custom_abbr": seg}, "name")
            if not cc:
                frappe.msgprint(f"[Warning] No Cost Center found for abbreviation '{seg}' for WBS item {code}.")
            doc.cost_center = cc

        boq_id_from_excel = row.get("BOQ ID")
        if pd.notna(boq_id_from_excel) and str(boq_id_from_excel).strip() != '':
            boq_id_str = str(boq_id_from_excel).strip()
            boq_details_doc_name = frappe.get_value("BOQ Details", {"boq_id": boq_id_str}, "name")
            if boq_details_doc_name and "boq_details" in valid_fields:
                doc.boq_details = boq_details_doc_name

        if is_item_like_wbs:
            item_code_from_excel = row.get("Item")
            truncated_item_code = str(item_code_from_excel)[:140] if pd.notna(item_code_from_excel) else None
            if "item_code" in valid_fields:
                doc.item_code = truncated_item_code
                existing_item_name = frappe.get_value("Item", {"item_code": truncated_item_code}, "name")
                if existing_item_name:
                    doc.item = existing_item_name

        for col, fld in column_map.items():
            if fld == "res_type":
                continue
            if is_item_like_wbs and col in ["Item Description", "Item"]:
                continue
            if col in df.columns and fld in valid_fields:
                val = row.get(col)
                if fld == "boq_id":
                    doc.set(fld, str(val).strip() if pd.notna(val) and str(val).strip() else None)
                elif fld in ["qty", "resource_qty", "waste", "custom_total_resource_qty", "unit_cost", "unit_rate"]:
                    try:
                        doc.set(fld, float(str(val).strip()) if pd.notna(val) and str(val).strip() else None)
                    except Exception:
                        frappe.msgprint(f"[Warning] Row {idx+2}: Invalid value '{val}' for '{fld}'")
                        doc.set(fld, None)
                else:
                    doc.set(fld, str(val).strip() if pd.notna(val) and str(val).strip() else None)

        try:
            doc.insert()
            frappe.db.set_value("BOQ", boq_name, "wbs_item_created", 1)
            frappe.db.commit()
            inserted[code] = doc.name
            inserted_docs.append({"cost_code": doc.cost_code, "name": doc.name, "level": doc.level})
            success += 1
        except Exception as e:
            frappe.msgprint(f"[Exception] Row {idx+2}: Error inserting {code} → {str(e)}")
            failed.append(f"Row {idx+2}: {code} (Insert Error: {e})")
            frappe.db.rollback()

    frappe.publish_realtime("import_progress", {"status": "Processing complete", "progress": 100})

    if failed:
        frappe.throw(f"Import completed with {success} successes and {len(failed)} failures. Errors: {', '.join(failed[:5])}{'...' if len(failed) > 5 else ''}")
    else:
        frappe.msgprint(f"Import completed successfully. {success} WBS items imported for BOQ: {boq_name}.")

    return {"total": total, "success": success, "failed": failed}

@frappe.whitelist()
def import_wbs_from_file_async(file_name, boq_name, project_name, warehouse):
    job = frappe.enqueue(
        "project_costing.project_costing.doctype.wbs_item.wbs_item_import.import_wbs_from_file",
        file_name=file_name,
        boq_name=boq_name,
        project_name=project_name,
        warehouse=warehouse,
        queue="long",
        timeout=3600  # 1 hour
    )
    return {"job_id": job.id}