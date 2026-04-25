function handler(event) {
  var request = event.request;
  var uri = request.uri;

  // Only browser page loads should be eligible for SPA fallback rewriting.
  // Mutating requests must pass through unchanged.
  if (!isAllowedMethod(request.method)) {
    return request;
  }

  // The function is attached only to frontend behaviors, but keep the path
  // check here too so the /app namespace remains the only rewrite target.
  if (!isAppRoute(uri)) {
    return request;
  }

  // Browser navigations ask for HTML. Generic fetch/API-style requests should
  // not be rewritten to the React entrypoint.
  if (!acceptsHtml(request.headers)) {
    return request;
  }

  // Asset paths contain filenames such as app.js or styles.css. Missing assets
  // should return real S3/CloudFront errors instead of index.html.
  if (looksLikeStaticAsset(uri)) {
    return request;
  }

  // React Router will handle the original /app route after the SPA loads.
  // CloudFront still fetches /index.html from the S3 origin.
  request.uri = '/index.html';
  return request;
}

function isAllowedMethod(method) {
  return method === 'GET' || method === 'HEAD';
}

function isAppRoute(uri) {
  return uri === '/app' || uri === '/app/' || uri.indexOf('/app/') === 0;
}

function acceptsHtml(headers) {
  var accept = headers.accept;

  if (!accept || !accept.value) {
    return false;
  }

  return accept.value.toLowerCase().indexOf('text/html') !== -1;
}

function looksLikeStaticAsset(uri) {
  var path = uri.split('?')[0];
  var lastSlash = path.lastIndexOf('/');
  var lastSegment = lastSlash === -1 ? path : path.substring(lastSlash + 1);

  return lastSegment.indexOf('.') !== -1;
}
