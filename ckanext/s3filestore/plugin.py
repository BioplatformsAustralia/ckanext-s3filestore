import os

from ckan.logic import ValidationError
from ckan.logic.validators import is_positive_integer
from routes.mapper import SubMapper
import ckan.plugins as plugins
import ckantoolkit as toolkit
import ckanext.s3filestore.action

import ckanext.s3filestore.uploader
from six import text_type


class S3FileStorePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.IUploader)
    plugins.implements(plugins.IRoutes, inherit=True)
    plugins.implements(plugins.IActions, inherit=True)

    # IConfigurer

    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')
        toolkit.add_resource('fanstatic', 's3filestore')

    # def update_config_schema(self, schema):
    #     # make it available to be editable at runtime
    #     ignore_missing = toolkit.get_validator('ignore_missing')
    #     is_positive_integer = toolkit.get_validator('is_positive_integer')
    #     schema.update({
    #         'ckanext.s3filestore.aws_limited_s3_expiry_in_seconds': [ignore_missing, is_positive_integer]
    #     })
    #     return schema

    # IConfigurable

    def configure(self, config):
        # Certain config options must exists for the plugin to work. Raise an
        # exception if they're missing.
        missing_config = "{0} is not configured. Please amend your .ini file."
        config_options = (
            'ckanext.s3filestore.aws_access_key_id',
            'ckanext.s3filestore.aws_secret_access_key',
            'ckanext.s3filestore.aws_bucket_name',
            'ckanext.s3filestore.region_name',
            'ckanext.s3filestore.signature_version',
            'ckanext.s3filestore.host_name',
            'ckanext.s3filestore.aws_limited_s3_access_key_id',
            'ckanext.s3filestore.aws_limited_s3_secret_access_key',
            'ckanext.s3filestore.aws_limited_s3_expiry_in_seconds'
        )
        for option in config_options:
            if not config.get(option, None):
                raise RuntimeError(missing_config.format(option))
        # Check that options actually work, if not exceptions will be raised
        if toolkit.asbool(
                config.get('ckanext.s3filestore.check_access_on_startup',
                           True)):
            ckanext.s3filestore.uploader.BaseS3Uploader().get_s3_bucket(
                config.get('ckanext.s3filestore.aws_bucket_name'))

        config_key = 'ckanext.s3filestore.aws_limited_s3_expiry_in_seconds'
        error_msg = "Config key: {0} must be a positive integer".format(config_key)
        try:
            pos_int_value = toolkit.asint((config.get(config_key, 0)))
            if pos_int_value < 1:
                raise ValidationError(error_msg)
        except ValueError:
            raise ValidationError(error_msg)

    # IUploader

    def get_resource_uploader(self, data_dict):
        '''Return an uploader object used to upload resource files.'''
        return ckanext.s3filestore.uploader.S3ResourceUploader(data_dict)

    def get_uploader(self, upload_to, old_filename=None):
        '''Return an uploader object used to upload general files.'''
        return ckanext.s3filestore.uploader.S3Uploader(upload_to,
                                                       old_filename)

    # IRoutes

    def before_map(self, map):
        with SubMapper(map, controller='ckanext.s3filestore.controller:S3Controller') as m:
            # Override the resource download links
            m.connect('resource_download',
                      '/dataset/{id}/resource/{resource_id}/download',
                      action='resource_download')
            m.connect('resource_download',
                      '/dataset/{id}/resource/{resource_id}/download/{filename}',
                      action='resource_download')

            # fallback controller action to download from the filesystem
            m.connect('filesystem_resource_download',
                      '/dataset/{id}/resource/{resource_id}/fs_download/{filename}',
                      action='filesystem_resource_download')

            # Intercept the uploaded file links (e.g. group images)
            m.connect('uploaded_file', '/uploads/{upload_to}/{filename}',
                      action='uploaded_file_redirect')

        return map

    # IActions
    def get_actions(self):
        return {'download_window': ckanext.s3filestore.action.download_window}
