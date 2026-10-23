
import os
import zipfile

dist_folder = "dist"
zip_name = "campusnetsim-dashboard-corrected.zip"

with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(dist_folder):
        for file in files:
            full_path = os.path.join(root, file)
            archive_path = os.path.relpath(full_path, dist_folder)
            archive_path = archive_path.replace("\\", "/")
            zf.write(full_path, archive_path)

print(f"Created {zip_name}")
