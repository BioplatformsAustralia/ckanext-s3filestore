# coding: utf8

from __future__ import unicode_literals

import logging
import os

import ckan.lib.uploader as uploader
from botocore.exceptions import ClientError
from ckan import authz
from ckan.logic import ValidationError, NotFound, NotAuthorized, side_effect_free, get_action

log = logging.getLogger(__name__)

from ckan.common import _

try:
    # CKAN 2.7 and later
    from ckan.common import config
except ImportError:
    # CKAN 2.6 and earlier
    from pylons import config

_default_404_message = 'Resource data not found'
_default_403_message = 'Unauthorized to read resource'


@side_effect_free
def download_window(context, data_dict):
    url_window_expiry_in_seconds = 600
    package_id = data_dict.get("package_id", False)
    resource_id = data_dict.get("resource_id", False)
    if not package_id:
        raise ValidationError("Missing package_id")
    if not resource_id:
        raise ValidationError("Missing resource_id")
    rsc = _get_authorised_resource(context, data_dict)
    if rsc.get('url_type') == 'upload':
        bucket, host_name, key_path, upload, filename = _get_s3_details(rsc)
        try:
            # Small workaround to manage downloading of large files
            # We are using redirect to minio's resource public URL
            # Open 10 min window
            url = _sign_and_return_s3_get(bucket, host_name, key_path, upload, url_window_expiry_in_seconds)
            log.info("have signed url: {0}".format(url))
            return {"url": url, "filename": filename, "expiry_in_seconds": url_window_expiry_in_seconds}
        except ClientError as ex:
            log.info('No filesystem fallback available in this route for resource {0}'
                     .format(resource_id))
            if ex.response['Error']['Code'] == 'NoSuchKey':
                raise NotFound(_default_404_message)
            else:
                log.error("Client error", ex)
                raise ex
    else:
        log.error("rsc did not return a url_type of 'upload.")
        raise NotFound(_default_404_message)


def _get_authorised_resource(context, data_dict):
    try:
        if (authz.is_authorized('resource_show', context, data_dict) and
                authz.is_authorized('package_show', context, data_dict)
        ):
            return get_action('resource_show')(context, {'id': data_dict.get("resource_id", "")})
        else:
            raise NotAuthorized(_default_403_message.format(id))
    except NotFound:
        raise NotFound(_default_404_message)
    except NotAuthorized:
        raise NotAuthorized(_default_403_message.format(id))


def _get_s3_details(rsc):
    upload = uploader.get_resource_uploader(rsc)
    bucket_name = config.get('ckanext.s3filestore.aws_bucket_name')
    host_name = config.get('ckanext.s3filestore.host_name')
    bucket = upload.get_s3_bucket_strict(bucket_name)
    filename = os.path.basename(rsc['url'])
    key_path = upload.get_path(rsc['id'], filename)
    key = filename
    if key is None:
        log.warn("Key '{0}' not found in bucket '{1}'"
                 .format(key_path, bucket_name))
    return bucket, host_name, key_path, upload, filename


def _sign_and_return_s3_get(bucket, host_name, key_path, upload, expiry_in_seconds):
    if not expiry_in_seconds:
        expiry_in_seconds = 60
    s3 = upload.get_s3_session()
    log.debug("key path is: {0}".format(key_path))
    client = s3.client(service_name='s3', endpoint_url=host_name)
    url = client.generate_presigned_url(ClientMethod='get_object',
                                        Params={'Bucket': bucket.name,
                                                'Key': key_path},
                                        ExpiresIn=expiry_in_seconds)
    return url
