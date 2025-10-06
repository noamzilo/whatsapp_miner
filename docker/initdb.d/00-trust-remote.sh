#!/bin/bash
# Allow all external connections without password (dev only)
echo "host all all all trust" >> /var/lib/postgresql/data/pg_hba.conf
