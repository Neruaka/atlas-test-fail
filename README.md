# baac-digest

Télécharge, valide et résume le fichier annuel des accidents corporels de la route (BAAC) publié
par l'ONISR : une seule commande, les mêmes chiffres sur toutes les machines. Sur le fichier 2023,
54 814 lignes valides et 8 lignes hors nomenclature écartées, en moins d'une seconde.

## Le problème

Voie Libre publie chaque automne un bilan des accidents de la route. Trois scripts écrits par
trois personnes donnaient trois totaux différents pour la même année, et le fichier 2023 contient
des lignes hors de la nomenclature officielle que personne n'avait repérées. `baac-digest` fait
le travail une fois, correctement : il vérifie l'empreinte du fichier, valide chaque ligne contre
un contrat de données tiré de la notice de l'ONISR, met de côté les lignes invalides avec leur
raison, et refuse de produire un bilan quand trop de lignes sont rejetées.

## Démo

Sortie réelle (Windows, chemins avec `\`) ; l'URL est coupée ici.

```text
$ uv run baac-digest download --year 2023 --out data/caract-2023.csv
INFO baac_digest.download: downloading https://static.data.gouv.fr/…/caract-2023.csv
INFO baac_digest.download: sha256 verified, wrote data\caract-2023.csv (6591826 bytes)

$ uv run baac-digest summarize data/caract-2023.csv --out out/2023
INFO baac_digest.pipeline: reading data\caract-2023.csv
INFO baac_digest.pipeline: 54822 lines read, 54814 valid, 8 rejected
INFO baac_digest.report: wrote out\2023\summary.json
INFO baac_digest.report: wrote out\2023\rejects.csv (8 rejected lines)

$ head -3 out/2023/rejects.csv
line,num_acc,errors
2757,202300002756,int='-1': Input should be greater than or equal to 1
2769,202300002768,int='-1': Input should be greater than or equal to 1
```

## Architecture

```text
cli.py       Typer : options, codes de sortie (0, 1, 2), logging sur la sortie d'erreur
download.py  registre des années (URL, sha256, mise à jour), lecture en mémoire, vérification,
             puis écriture ; read_url, la seule fonction qui touche au réseau
pipeline.py  encodage, en-tête, lecture ligne à ligne, agrégats (rien sur le disque)
model.py     Accident : le contrat de données Pydantic, seul endroit où vivent les règles
report.py    summary.json puis rejects.csv
errors.py    InputError (code 2), DownloadError (code 1)
```

Seul `cli.py` connaît les codes de sortie : les autres modules lèvent des exceptions métier.

## Résultats

Sur le fichier 2023 complet (54 822 lignes, sha256 `e6cb8685…4a87ac0`) :

| Mesure | Valeur |
|---|---|
| lignes lues | 54 822 |
| lignes valides | 54 814 |
| lignes rejetées | 8 (6 `int` à -1, 2 `lum` à -1 : codes absents de la notice) |
| durée de `summarize` | 0,7 s sur un laptop i7 (démarrage compris), pour 30 s exigées |
| couverture des tests | 97 % des lignes du paquet (49 tests, 3 s avec la mesure de couverture) |

Données : ONISR (Observatoire national interministériel de la sécurité routière), fichier BAAC des
caractéristiques des accidents corporels, sur data.gouv.fr, sous Licence Ouverte / Open Licence
(Etalab). Dernière mise à jour des fichiers : 28 octobre 2024 (2023) et 21 octobre 2025 (2024).

## Lancer le projet

```sh
git clone <url-du-repo> baac-digest && cd baac-digest
uv sync                                   # Python 3.14 (.python-version) et dépendances (uv.lock)
uv run baac-digest download --year 2023 --out data/caract-2023.csv
uv run baac-digest summarize data/caract-2023.csv --out out/2023
uv run pytest --cov=baac_digest           # tests, sans réseau
uv run pre-commit install                 # Ruff avant chaque commit
cp .env.example .env                      # puis choisis POSTGRES_PASSWORD
docker compose up                         # Postgres (127.0.0.1:5432) et Jupyter (127.0.0.1:8888)
```

Codes de sortie : 0 succès ; 1 porte de qualité fermée (`--max-reject-rate`, 0,01 par défaut) ou
téléchargement refusé ; 2 entrée inutilisable ou usage invalide.

## Choix techniques

- **Le module `csv` plutôt que pandas** : 55 000 lignes se lisent ligne à ligne, et chaque ligne
  garde son numéro pour `rejects.csv`.
- **Pydantic pour le contrat** : les règles sont déclarées une fois, dans `model.py`, avec les
  libellés de la notice ; `dep` reste une chaîne, puisque `01` et `2A` ne sont pas des nombres.
  Chaque rejet nomme la colonne et la valeur lue.
- **Téléchargement vérifié en mémoire** : 6,6 Mo tiennent sans peine ; rien n'est écrit avant la
  vérification du sha256, donc un fichier déjà présent n'est jamais remplacé par un fichier
  tronqué ou modifié.
- **`uv sync --locked` en CI**, `uv sync --frozen` chez le vérificateur : la CI échoue dès que
  `uv.lock` ne correspond plus à `pyproject.toml`.

Limites assumées : `com`, `atm`, `col` et `adr` ne sont pas vérifiées, ni les doublons de
`Num_Acc` (extensions) ; l'écriture n'est pas atomique (une coupure en pleine écriture peut
laisser un fichier incomplet, que le sha256 refusera au prochain téléchargement) ; le fichier 2025
s'ajoutera au registre de `download.py` à sa publication.

## Usage de l'IA

Aucun code généré. Questions posées au tuteur, ce qu'elles m'ont appris, et comment je l'ai
vérifié :

- Pourquoi `Literal[1, 2]` refuse la chaîne `"1"` : Pydantic compare un `Literal` sans convertir.
  Vérifié par un test sur une vraie ligne du fichier, recopiée avec ses chaînes.
- La différence entre `uv sync --locked` et `--frozen` : `--locked` échoue si `uv.lock` n'est plus
  à jour, `--frozen` l'applique sans le comparer. Vérifié en modifiant `pyproject.toml` sans
  relancer `uv lock`.

Le code est sous licence MIT (`LICENSE`).
