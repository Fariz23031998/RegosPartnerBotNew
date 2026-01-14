#!/bin/bash

# Docker helper script for RegosPartnerBot

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists
if [ ! -f .env ]; then
    print_warn ".env file not found. Creating from env.example..."
    cp env.example .env
    print_info "Please edit .env file and set your configuration before continuing."
    exit 1
fi

# Create necessary directories
print_info "Creating data directories..."
mkdir -p data exports

# Function to start services
start() {
    print_info "Starting Docker containers..."
    docker-compose up -d
    print_info "Containers started. Use 'docker-compose logs -f' to view logs."
}

# Function to stop services
stop() {
    print_info "Stopping Docker containers..."
    docker-compose down
    print_info "Containers stopped."
}

# Function to restart services
restart() {
    print_info "Restarting Docker containers..."
    docker-compose restart
    print_info "Containers restarted."
}

# Function to view logs
logs() {
    docker-compose logs -f "$@"
}

# Function to rebuild and restart
rebuild() {
    print_info "Rebuilding and restarting containers..."
    docker-compose up -d --build
    print_info "Containers rebuilt and restarted."
}

# Function to show status
status() {
    print_info "Container status:"
    docker-compose ps
}

# Function to show help
help() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start      Start Docker containers"
    echo "  stop       Stop Docker containers"
    echo "  restart    Restart Docker containers"
    echo "  logs       View container logs (add service name for specific service)"
    echo "  rebuild    Rebuild and restart containers"
    echo "  status     Show container status"
    echo "  help       Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start"
    echo "  $0 logs backend"
    echo "  $0 rebuild"
}

# Main command handler
case "${1:-help}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    logs)
        logs "${@:2}"
        ;;
    rebuild)
        rebuild
        ;;
    status)
        status
        ;;
    help|--help|-h)
        help
        ;;
    *)
        print_error "Unknown command: $1"
        help
        exit 1
        ;;
esac
