# coding: utf8

from __future__ import unicode_literals

import logging
import os

import ckan.lib.uploader as uploader
import ckan.lib.helpers as h
import ckan.logic.converters as converters
from botocore.exceptions import ClientError
from ckan import authz, config
from ckan.logic import NotFound, NotAuthorized, side_effect_free, get_action, validate
from ckan.lib.base import request
from werkzeug.routing import Map, Rule
from six.moves.urllib.parse import (
    urlparse,
)

from .logic import schema

log = logging.getLogger(__name__)

try:
    # CKAN 2.7 and later
    from ckan.common import config
except ImportError:
    # CKAN 2.6 and earlier
    from pylons import config

_default_404_message = "Resource data not found"
_default_403_message = "Unauthorized to read resource"


@validate(schema.s3filestore_download_window)
@side_effect_free
def download_window(context, data_dict):
    local = False
    rsc = _get_authorised_resource(context, data_dict)

    # Bail early if we have a garbage URL in the resource, throw an error
    if not h.is_url(rsc["url"]):
        log.error(
            "Resource {0} does not contain a valid URL {1}".format(
                rsc["id"], rsc["url"]
            )
        )
        raise NotFound(_default_404_message)

    # Return a response with the remote URL if not local
    if not h.url_is_local(rsc["url"]):
        local = False
        url = rsc["url"]
        expiry_in_seconds = None
        filename = os.path.basename(rsc["url"])

        log.info("Have a remote URL: {0}".format(url))
        return {
            "url": url,
            "filename": filename,
            "expiry_in_seconds": expiry_in_seconds,
            "local": local,
        }

    local = True

    # Check if matches our URL pattern
    m = Map(
        [
            Rule(
                "/dataset/<id>/resource/<resource_id>/download/<filename>",
                endpoint="resource_download",
            ),
        ]
    )

    # /dataset/bpa-mm-metagenomics-36116/resource/f5f811d3aecbad91328965c684e6894f/download/MM_metagenomics_UNSW_HTCGWBCXY_checksums.md5
    # {'id': 'bpa-mm-metagenomics-36116', 'resource_id': 'f5f811d3aecbad91328965c684e6894f', 'filename': 'MM_metagenomics_UNSW_HTCGWBCXY_checksums.md5'})

    url_pattern = m.bind(config.get("ckan.site_url"), "/")
    parsed_url = urlparse(rsc["url"])
    try:
        matched_url = url_pattern.match(parsed_url.path)[1]
    except:
        log.error(
            "Resource {0} does not contain a valid resource download URL {1}".format(
                rsc["id"], rsc["url"]
            )
        )
        raise NotFound(_default_404_message)

    if rsc.get("url_type") == "upload":
        # Sanity check - if url_type is upload, must match packages
        dd_id = converters.convert_package_name_or_id_to_id(data_dict.get("package_id"), context)
        pr_id = converters.convert_package_name_or_id_to_id(matched_url.get("id"), context)

        if dd_id != pr_id:
            log.error(
                "Resource {0} does not contain a valid package for URL {1}".format(
                    rsc["id"], rsc["url"]
                )
            )
            raise NotFound(_default_404_message)
    else:
        # It appears to be a shared resource, recurse to enforce context
        # Sanity check that resource IDs are different
        if rsc["id"] == matched_url.get("resource_id"):
            log.error(
                "Resource {0} are the same for URL {1}, cannot recurse".format(
                    rsc["id"], rsc["url"]
                )
            )
            raise NotFound(_default_404_message)

        return get_action("download_window")(
            context,
            {
                "package_id": matched_url.get("id", ""),
                "resource_id": matched_url.get("resource_id", ""),
            },
        )

    bucket, host_name, key_path, upload, filename = _get_s3_details(rsc)
    try:
        # Small workaround to manage downloading of large files
        # We are using redirect to minio's resource public URL
        url, expiry_in_seconds = _sign_and_return_s3_get(
            bucket, host_name, key_path, upload
        )
        log.info("have signed url: {0}".format(url))
        return {
            "url": url,
            "filename": filename,
            "expiry_in_seconds": expiry_in_seconds,
            "local": local,
        }
    except ClientError as ex:
        # FIXME Does this error message make sense????
        log.info(
            "No filesystem fallback available in this route for resource {0}".format(
                resource_id
            )
        )
        if ex.response["Error"]["Code"] == "NoSuchKey":
            raise NotFound(_default_404_message)
        else:
            log.error("Client error", ex)
            raise ex


def _get_authorised_resource(context, data_dict):
    try:
        return get_action("resource_show")(
            context, {"id": data_dict.get("resource_id", "")}
        )
    except NotFound:
        raise NotFound(_default_404_message)
    except NotAuthorized:
        raise NotAuthorized(_default_403_message.format(id))
    except Exception as e:
        # this will send back as 500 error at this layer rather than status from lower level
        raise Exception(e)


def _get_s3_details(rsc):
    upload = uploader.get_resource_uploader(rsc)
    bucket_name = config.get("ckanext.s3filestore.aws_bucket_name")
    host_name = config.get("ckanext.s3filestore.host_name")
    bucket = upload.get_strict_s3_bucket(bucket_name)
    filename = os.path.basename(rsc["url"])
    key_path = upload.get_path(rsc["id"], filename)
    key = filename
    if key is None:
        log.warn("Key '{0}' not found in bucket '{1}'".format(key_path, bucket_name))
    return bucket, host_name, key_path, upload, filename


def _sign_and_return_s3_get(bucket, host_name, key_path, upload):
    expiry_in_seconds = config.get(
        "ckanext.s3filestore.aws_limited_s3_expiry_in_seconds", 60
    )
    s3 = upload.get_limited_s3_session()

    log.debug("key path is: {0}".format(key_path))
    client = s3.client(service_name="s3", endpoint_url=host_name)
    url = client.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": bucket.name, "Key": key_path},
        ExpiresIn=expiry_in_seconds,
    )
    return url, expiry_in_seconds
