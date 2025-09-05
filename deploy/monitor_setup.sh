#!/bin/bash

# SNOBot Database Setup Monitor
# Use this script to monitor the database initialization progress

echo "SNOBot Database Setup Monitor"
echo "============================="
echo ""
echo "This will show real-time progress of database initialization."
echo "Press Ctrl+C to stop monitoring."
echo ""

# Function to show current status
show_status() {
    echo "Current Status:"
    echo "---------------"
    
    # Check if SQL database exists
    if [ -f "/opt/snobot/resources/omop_vocab/omop_vocab.duckdb" ]; then
        sql_size=$(du -h /opt/snobot/resources/omop_vocab/omop_vocab.duckdb | cut -f1)
        echo "✓ SQL Database: $sql_size"
    else
        echo "⏳ SQL Database: Not created yet"
    fi
    
    # Check if ChromaDB exists
    if [ -d "/opt/snobot/resources/omop_vocab/chroma_db" ]; then
        chroma_size=$(du -sh /opt/snobot/resources/omop_vocab/chroma_db | cut -f1)
        echo "✓ Vector Database: $chroma_size"
    else
        echo "⏳ Vector Database: Not created yet"
    fi
    
    echo ""
}

# Show initial status
show_status

echo "Live Application Logs:"
echo "====================="
echo ""

# Follow the logs
tail -f /var/log/snobot/snobot.log | grep -E "(SqlDB|VecDB|Processed|Loading|initialization)"
