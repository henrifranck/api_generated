#!/bin/bash

# Exécute les tests seulement si TESTING=1
if [ "$TESTING" -eq 1 ]; then
    echo "Running tests..."
    pytest tests/ --cov=app -v
    if [ $? -ne 0 ]; then
        echo "Tests failed, exiting..."
        exit 1
    fi
    echo "Tests passed!"
else
    echo "Skipping tests (TESTING=0)"
fi

# Exécute le script original
exec "$@"