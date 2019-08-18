twisted.web.server.Request will now use twisted.web.server.Site.getContentFile, if it exists, to get a file into which to write request content.  If getContentFile is not provided by the site, it will fall back to the previous behavior of using io.BytesIO for small requests and tempfile.TemporaryFile for large ones.