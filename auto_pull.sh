#!/bin/bash
cd "$(dirname "$0")" || exit 1
echo "[AUTO PULL] Inizio aggiornamento..."
git fetch origin main
git reset --hard origin/main
git clean -fd
echo "[AUTO PULL] Completato. Riavvio voce-ai..."
systemctl restart voce-ai

