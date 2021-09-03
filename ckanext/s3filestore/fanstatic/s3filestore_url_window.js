'use strict';
console.log('testing')

ckan.module('s3filestore_url_window', function ($) {
    return {
        _snippetReceived: false,
        initialize: function () {
            $.proxyAll(this, /_on/);
            this.el.on('click', this._onClick);
        },
        _onClick: function (event) {
            this.sandbox.client.call('GET', 'download_window',
                '?package_id=' + this.options.id + '&resource_id=' + this.options.rid,
                this._onReceiveApiSnippet,
                this._onReceiveApiSnippetError
            );
        },
        _onReceiveApiSnippet: function (response) {
            if (response.result) {
                this.options["result"] = response.result
            }
            this.sandbox.client.getTemplate('s3filestore_url_window.html',
                this.options,
                this._onReceiveHtmlSnippet,
                this._onReceiveHtmlSnippetError
            );
        },
        _onReceiveHtmlSnippet: function (html) {
            this._toggleFeedback(html);
            // this.el[0].innerHTML = html;
        },
        _onReceiveApiSnippetError: function (error) {
            this._onReceiveSnippetError(error, 'Api');
        },
        _onReceiveHtmlSnippetError: function (error) {
            this._onReceiveSnippetError(error, 'Html');
        },
        _onReceiveSnippetError: function (error, type) {
            let content = `ERROR (${type}): ${error.status} ${error.statusText}`;
            this._toggleFeedback(content);
        },
        _toggleFeedback: function (message) {
            this.el.popover('destroy');
            let title = 'testing';
            if (this._snippetReceived) {
                title = 'testing completed';
            }
            this.el.popover({
                title: title,
                html: true,
                content: message,
                placement: 'left'
            });
            this.el.popover('show');
        }
    };
});
