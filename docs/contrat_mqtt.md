# Contrat MQTT (Digi4 → Digi5)
**Projet :** SANTÉ OS — Système de Détection de Malaise en EHPAD

## 1. Correspondance des topics et formats (Option A)

| Élément | Valeur dans votre projet EHPAD actuel (simulateur Python) | Valeur retenue pour le firmware ESP32 (Digi5) |
| :--- | :--- | :--- |
| **Préfixe / racine des topics** | `ehpad/residents/` | `ehpad/residents/` |
| **Topic des constantes** | `ehpad/residents/<id>/vitals` | `ehpad/residents/<id>/vitals` |
| **Topic des alertes** | `ehpad/alerts` | `ehpad/alerts` |
| **Topic d'état du device** | *(Absent dans le simulateur Python)* | `ehpad/device/<device_id>/status` |
| **Clé de la FC** | `heart_rate` | `heart_rate` |
| **Clé de l'horodatage et format** | `timestamp` ISO 8601 UTC (`...Z`) | `timestamp` ISO 8601 UTC (`...Z`) |
| **Niveaux d'alerte** | 1 à 5 | `info` / `warning` / `danger` (à mapper côté dashboard) |
| **Broker, port, TLS** | MQTT-Broker local (Port 1883) | broker.hivemq.com (Port 1883, sans TLS pour Wokwi) |

## 2. Structure JSON attendue (Payloads)

### A. Flux des constantes (`.../vitals`)
Le payload généré par l'ESP32 doit reprendre les clés principales attendues par le backend IA (les clés comme `systolic_bp`, `glucose`, ou `fall_detected` qui ne sont pas mesurées par ce montage simple peuvent être gérées de manière générique dans un second temps, mais l'ESP doit a minima renvoyer les données vitales mesurées).

```json
{
  "resident_id": "P001",
  "heart_rate": 85,
  "movement_level": 45,
  "timestamp": "2026-10-02T13:31:04Z",
  "alert_level": 0
}