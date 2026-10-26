FROM nginx:alpine
COPY web/index.html /usr/share/nginx/html/index.html
COPY web/app.js /usr/share/nginx/html/app.js
COPY README.md /usr/share/nginx/html/README.md
COPY specs /usr/share/nginx/html/specs
COPY templates /usr/share/nginx/html/templates
COPY assets/cvs /usr/share/nginx/html/assets/cvs
EXPOSE 80
