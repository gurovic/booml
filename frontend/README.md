# frontend

## Project setup
```
npm install
```

### Compiles and hot-reloads for development
```
npm run serve
```

### Compiles and minifies for production
```
npm run build
```

### Lints and fixes files
```
npm run lint
```

## Production Deployment

**IMPORTANT**: For production deployments, you MUST use a production build, not the dev server.

### Correct Production Setup

1. Build the production bundle:
   ```bash
   npm run build
   ```

2. Serve the `dist/` directory using a static file server (nginx, Apache, etc.)

3. Configure your web server to:
   - Serve static files from `dist/`
   - Proxy API requests to the backend
   - Set appropriate cache headers for static assets

### ⚠️ Common Mistakes

**DO NOT** run `npm run serve` in production! This will:
- Enable Hot Module Replacement (HMR)
- Cause infinite reload loops when HMR files are not found
- Use unminified, unoptimized code
- Expose development tools and debug information

If you must run the dev server in a production-like environment, set `NODE_ENV=production`:
```bash
NODE_ENV=production npm run serve
```

This will disable HMR and prevent reload loops (though it's still not recommended for actual production).

### Example nginx Configuration

```nginx
server {
    listen 80;
    server_name booml.letovo.site;
    root /path/to/frontend/dist;
    
    # Serve static files
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # Proxy API requests to backend
    location /api/ {
        proxy_pass http://backend:8100;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /backend/ {
        proxy_pass http://backend:8100;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Customize configuration
See [Configuration Reference](https://cli.vuejs.org/config/).
