#!/bin/bash
# Quick-start script for News Intelligence System
# Handles environment setup, builds, and service startup

set -e

PROJECT_NAME="News Intelligence System"
COMPOSE_FILE="docker-compose.yml"
ENV_FILE="backend/.env"
ENV_EXAMPLE="backend/.env.example"

echo "=================================="
echo "  $PROJECT_NAME - Quick Start"
echo "=================================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker Desktop."
    exit 1
fi
if ! command -v docker-compose &> /dev/null; then
    echo "⚠️  docker-compose not found (docker compose instead)"
fi
echo "✓ Docker available"

# Setup environment file
if [ ! -f "$ENV_FILE" ]; then
    echo ""
    echo "Setting up environment file..."
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    echo "✓ Created $ENV_FILE (using development defaults)"
    echo ""
    echo "⚠️  IMPORTANT: Update these in $ENV_FILE for production:"
    echo "   - SECRET_KEY: generate with: openssl rand -hex 32"
    echo "   - NEWSAPI_KEY: get from https://newsapi.org"
    echo "   - GNEWS_API_KEY: get from https://gnews.io"
    echo "   - SMTP_* credentials: for email notifications"
else
    echo "✓ Environment file exists ($ENV_FILE)"
fi

echo ""
echo "Building Docker images..."
docker compose -f "$COMPOSE_FILE" build

echo ""
echo "Starting services..."
docker compose -f "$COMPOSE_FILE" up -d

echo ""
echo "Waiting for services to be healthy..."
for i in {1..60}; do
    if docker compose -f "$COMPOSE_FILE" exec -T backend curl -f http://localhost:8080/api/health &> /dev/null; then
        echo "✓ Backend is ready"
        break
    fi
    if [ $i -eq 60 ]; then
        echo "❌ Backend did not become ready"
        exit 1
    fi
    echo "  Waiting... ($i/60)"
    sleep 1
done

echo ""
echo "✓ All services are running!"
echo ""
echo "Access your application:"
echo "  Frontend:   http://localhost:3000"
echo "  Backend:    http://localhost:8080"
echo "  API Docs:   http://localhost:8080/docs"
echo "  MongoDB:    mongodb://localhost:27017"
echo ""
echo "Quick links:"
echo "  View logs:     docker compose logs -f backend"
echo "  Stop services: docker compose down"
echo "  Run tests:     python test_system_integration.py"
echo ""
echo "📚 Documentation: see SYSTEM_UPDATE_v2.0.md"
