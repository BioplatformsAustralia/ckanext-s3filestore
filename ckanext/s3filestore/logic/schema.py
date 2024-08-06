import ckan.plugins.toolkit as tk
from six import text_type


def s3filestore_download_window():
    not_empty = tk.get_validator("not_empty")
    resource_id_exists = tk.get_validator("resource_id_exists")
    package_id_or_name_exists = tk.get_validator("package_id_or_name_exists")

    return {
        "package_id": [
            not_empty,
            text_type,
            package_id_or_name_exists,
        ],
        "resource_id": [not_empty, text_type, resource_id_exists],
    }
