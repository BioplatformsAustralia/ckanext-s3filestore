'use strict';
console.log('testing')

function clickCopyS3URL(e) {
    alert(e.className);
    // var copyText = e;
    // // /* Select the text field */
    // copyText.select();
    // copyText.setSelectionRange(0, 99999); /* For mobile devices */
    // //
    // // /* Copy the text inside the text field */
    // navigator.clipboard.writeText(copyText.value);
    const toCopy = jQuery(e).find('.fa-copy').attr('data-content');
    alert(toCopy);
    navigator.clipboard.writeText(toCopy);
    // /* Alert the copied text */
    // alert("Copied the text: " + copyText.value);
}

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
                for (const [key, value] of Object.entries(response.result)) {
                    this.options[key] = value;
                }
            }
            this.sandbox.client.getTemplate('s3filestore_url_window.html',
                this.options,
                this._onReceiveHtmlSnippet,
                this._onReceiveHtmlSnippetError
            );
        },
        _onReceiveHtmlSnippet: function (html) {
            // alert($(this.el[0]).closest('div'));
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
            let element = $(this.el[0]).closest('div')
            element.popover('destroy');
            let title = 'testing';
            // if (this._snippetReceived) {
            //     title = 'testing completed';
            // }
            // element = $(this.el[0]).closest('.explore').find('.download-window-icon')
            // element.html(message)
            element.popover({
                title: "Copy S3 URL",
                html: true,
                content: message,
                placement: 'left'
            });
            // element.attr('data-trigger', 'click')
            element.popover('show');
            // $('.popover').one('click', function(){
            //     element.popover('destroy');
            // });
        }
    };
});
