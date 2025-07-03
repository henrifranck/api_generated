import os
import shutil


def move_migration_files(source_dir, target_dir):
    """
    Déplace tous les fichiers de migration de `source_dir` vers `target_dir`.
    """
    # Vérifier si le répertoire source existe
    if not os.path.exists(source_dir):
        print(f"Le répertoire source n'existe pas : {source_dir}")
        return

    # Vérifier si le répertoire cible existe, sinon le créer
    if not os.path.exists(target_dir):
        print(f"Le répertoire cible n'existe pas. Création de : {target_dir}")
        os.makedirs(target_dir)

    # Lister tous les fichiers dans le répertoire source
    migration_files = os.listdir(source_dir)

    # Déplacer chaque fichier
    for file_name in migration_files:
        source_file = os.path.join(source_dir, file_name)
        target_file = os.path.join(target_dir, file_name)

        # Déplacer le fichier
        shutil.move(source_file, target_file)
        print(f"Déplacé : {source_file} -> {target_file}")

    print("Tous les fichiers ont été déplacés avec succès !")
