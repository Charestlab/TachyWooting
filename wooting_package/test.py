#!/usr/bin/env python3
"""
Vérification rapide des chemins Wooting - Version simplifiée
Modifiez les variables ci-dessous puis exécutez le script
"""

import os
import glob

# ========================================
# MODIFIEZ CES CHEMINS SELON VOTRE SYSTÈME
# ========================================

# Chemin de base vers vos bibliothèques Wooting
BASE_PATH = "/home/labtech/projects/Analog_keyboard_measurement/wooting_package/libraries/linux"

# Chemin vers le répertoire des plugins
PLUGINS_PATH = os.path.join(BASE_PATH, "plugins")

# Répertoire de sortie pour l'interface compilée
INTERFACE_PATH = "/home/labtech/projects/Analog_keyboard_measurement/wooting_package/interface"

# ========================================
# VÉRIFICATION AUTOMATIQUE
# ========================================

def check_path(path, name, is_file=False):
    """Vérifie si un chemin existe."""
    exists = os.path.exists(path)
    if is_file:
        exists = exists and os.path.isfile(path)
    else:
        exists = exists and os.path.isdir(path)
    
    status = "✅" if exists else "❌"
    print(f"{status} {name}: {path}")
    return exists

def check_files_in_directory(directory, pattern, name):
    """Vérifie les fichiers dans un répertoire."""
    if not os.path.exists(directory):
        print(f"❌ {name}: Répertoire {directory} n'existe pas")
        return []
    
    files = glob.glob(os.path.join(directory, pattern))
    if files:
        print(f"✅ {name} ({len(files)} fichiers trouvés):")
        for f in files:
            size = os.path.getsize(f)
            print(f"   - {os.path.basename(f)} ({size} bytes)")
    else:
        print(f"❌ {name}: Aucun fichier trouvé avec le pattern {pattern}")
    
    return files

def main():
    print("=" * 60)
    print("VÉRIFICATION RAPIDE DES CHEMINS WOOTING")
    print("=" * 60)
    
    print("Configuration actuelle:")
    print(f"Base: {BASE_PATH}")
    print(f"Plugins: {PLUGINS_PATH}")
    print(f"Interface: {INTERFACE_PATH}")
    print()
    
    # Vérifier les répertoires
    all_good = True
    
    print("Vérification des répertoires:")
    all_good &= check_path(BASE_PATH, "Répertoire de base")
    all_good &= check_path(PLUGINS_PATH, "Répertoire plugins")
    
    # Créer le répertoire interface s'il n'existe pas
    if not os.path.exists(INTERFACE_PATH):
        try:
            os.makedirs(INTERFACE_PATH, exist_ok=True)
            print(f"✅ Répertoire interface créé: {INTERFACE_PATH}")
        except Exception as e:
            print(f"❌ Impossible de créer le répertoire interface: {e}")
            all_good = False
    else:
        print(f"✅ Répertoire interface: {INTERFACE_PATH}")
    
    print("\nVérification des fichiers:")
    
    # Vérifier les headers
    headers = [
        "wooting-analog-common.h",
        "wooting-analog-wrapper.h"
    ]
    
    for header in headers:
        header_path = os.path.join(BASE_PATH, header)
        all_good &= check_path(header_path, f"Header {header}", is_file=True)
    
    # Vérifier les bibliothèques (.so pour Linux)
    so_files = check_files_in_directory(BASE_PATH, "*.so", "Bibliothèques .so")
    if not so_files:
        all_good = False
    
    # Vérifier les plugins
    plugin_files = check_files_in_directory(PLUGINS_PATH, "*.so", "Plugins .so")
    if not plugin_files:
        print("⚠️  Pas de plugins trouvés (peut être normal pour certaines configurations)")
    
    print("\n" + "=" * 60)
    if all_good:
        print("🎉 TOUT EST PRÊT ! Vous pouvez maintenant:")
        print("1. Utiliser ces chemins dans votre script de test")
        print("2. Ou créer un fichier .env avec ces valeurs")
        print("3. Puis lancer la compilation de l'interface")
        
        print(f"\nPour votre script de test, utilisez:")
        print(f"os.environ['WOOTING_ANALOG_PLUGINS_DIR'] = '{PLUGINS_PATH}'")
        print(f"os.environ['WOOTING_ANALOG_SDK_DIR'] = '{BASE_PATH}'")
        
    else:
        print("❌ DES PROBLÈMES ONT ÉTÉ DÉTECTÉS")
        print("Vérifiez les chemins marqués d'un ❌ ci-dessus")
        print("Modifiez les variables en haut du script si nécessaire")
    
    return 0 if all_good else 1

if __name__ == "__main__":
    exit(main())