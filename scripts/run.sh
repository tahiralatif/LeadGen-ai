#!/bin/bash

# LeadGen Agent Runner Script

# Activate virtual environment
source venv/bin/activate

# Check for command
if [ $# -eq 0 ]; then
    echo "Usage: ./run.sh <command> [args]"
    echo ""
    echo "Commands:"
    echo "  find-leads     Find and verify leads"
    echo "  send-campaign  Send email campaign"
    echo "  check-responses Check for responses"
    echo "  stats          Show statistics"
    echo "  server         Start API server"
    exit 1
fi

# Run command
case $1 in
    find-leads)
        python -m src.main find-leads "${@:2}"
        ;;
    send-campaign)
        python -m src.main send-campaign "${@:2}"
        ;;
    check-responses)
        python -m src.main check-responses "${@:2}"
        ;;
    stats)
        python -m src.utils.analytics "${@:2}"
        ;;
    server)
        uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload
        ;;
    *)
        echo "Unknown command: $1"
        exit 1
        ;;
esac