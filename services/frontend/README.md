# Dengue Knowledge Graph Frontend

Web-based user interface for the Dengue Knowledge Graph project, providing interactive visualization and exploration of dengue fever data.

## Features

- Interactive knowledge graph visualization
- Dengue classification and symptom exploration
- Geographic risk visualization
- Treatment protocol reference
- Integration with agent workflow for guided exploration

## Development

### Prerequisites

- Node.js 18+
- npm 9+

### Local Development

```bash
# Install dependencies
npm install

# Start development server
npm start
```

The development server will be available at http://localhost:3000

### Building for Production

```bash
# Create optimized production build
npm run build
```

### Container Development

Following project standards, the frontend can be built and run using Podman with Red Hat UBI base images:

```bash
# Build the container
podman build -t dengue-frontend:local -f Containerfile .

# Run the container
podman run -d --name frontend-service \
  -p 8080:8080 \
  dengue-frontend:local
```

## Container Structure

The frontend uses a multi-stage build process:
1. Build stage using UBI9/Node.js 18 to compile the React application
2. Production stage using UBI9/Nginx 1.20 to serve the static assets

This follows the project standard of using Red Hat UBI base images for all containers.

## Deployment

This service is deployed as part of the Dengue Knowledge Graph project using ArgoCD. The deployment configuration can be found in the `deployment/services/frontend` directory.
