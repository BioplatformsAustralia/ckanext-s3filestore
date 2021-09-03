# coding: utf8

from __future__ import unicode_literals
import logging
import os

import ckan.lib.base as base
import ckan.lib.uploader as uploader
import ckan.logic
import ckan.model as model
from botocore.exceptions import ClientError
from ckan import authz
from ckan.common import c

from ckan.logic import side_effect_free

log = logging.getLogger(__name__)

NotFound = ckan.logic.NotFound
NotAuthorized = ckan.logic.NotAuthorized
get_action = ckan.logic.get_action
abort = base.abort

from ckan.common import _

try:
    # CKAN 2.7 and later
    from ckan.common import config
except ImportError:
    # CKAN 2.6 and earlier
    from pylons import config


# TODO: refactored borrowed logic into new methods: once updates are in PROD and stable consider using new
#  methods for other functions here

@side_effect_free
def download_window(context, data_dict):
    package_id = data_dict.get("package_id", False)
    resource_id = data_dict.get("resource_id", False)
    filename = data_dict.get("resource_id", None)
    if not package_id:
        raise ckan.logic.ValidationError("Missing package_id")
    if not resource_id:
        raise ckan.logic.ValidationError("Missing resource_id")
    rsc = _get_authorised_resource(context, data_dict)

    if rsc.get('url_type') == 'upload':
        bucket, host_name, key_path, upload = _get_s3_details(filename, rsc)

        try:
            # Small workaround to manage downloading of large files
            # We are using redirect to minio's resource public URL
            # Open 30 min window
            url = _sign_and_return_s3_get(bucket, host_name, key_path, upload, 1800)
            log.info("have signed url: {0}".format(url))
            print("have signed url: {0}".format(url))
            return url

        except ClientError as ex:
            log.info('No filesystem fallback are available in this route for resource {0}'
                     .format(resource_id))
            if ex.response['Error']['Code'] == 'NoSuchKey':
                abort(404, _('Resource data not found'))
            else:
                raise ex
    elif 'url' not in rsc:
        abort(404, _('No download is available'))


def _get_authorised_resource(context, data_dict):
    try:
        if (authz.is_authorized('resource_show', context, data_dict) and
                authz.is_authorized('package_show', context, data_dict)
        ):
            return get_action('resource_show')(context, {'id': data_dict.get("resource_id", "")})
        else:
            abort(401, _('Unauthorized to read resource %s') % id)
    except NotFound:
        abort(404, _('Resource not found'))
    except NotAuthorized:
        abort(401, _('Unauthorized to read resource %s') % id)


def _get_s3_details(filename, rsc):
    upload = uploader.get_resource_uploader(rsc)
    bucket_name = config.get('ckanext.s3filestore.aws_bucket_name')
    # TODO: we put region into our hostname so not needed, unlike upstream forks. remove variable as not used
    # region = config.get('ckanext.s3filestore.region_name')
    host_name = config.get('ckanext.s3filestore.host_name')
    bucket = upload.get_s3_bucket_strict_test(bucket_name)
    if filename is None:
        filename = os.path.basename(rsc['url'])
    key_path = upload.get_path(rsc['id'], filename)
    key = filename
    if key is None:
        log.warn('Key \'{0}\' not found in bucket \'{1}\''
                 .format(key_path, bucket_name))
    return bucket, host_name, key_path, upload


def _sign_and_return_s3_get(bucket, host_name, key_path, upload, expiryInSeconds):
    if not expiryInSeconds:
        expiryInSeconds = 60
    s3 = upload.get_s3_session_test()
    print("key path is: {0}".format(key_path))
    client = s3.client(service_name='s3', endpoint_url=host_name)
    url = client.generate_presigned_url(ClientMethod='get_object',
                                        Params={'Bucket': bucket.name,
                                                'Key': key_path},
                                        ExpiresIn=expiryInSeconds)
    return url
