"""Génère les documents fictifs de la démo « IA et analyse de plans ».

Tout est fictif (CH de Valmont, BE Alpha Ingénierie) : aucun document client n'est utilisé.

Sorties dans documents/ :
- plan-salle3-indA.pdf / .png et plan-salle3-indB.pdf / .png : plan d'aménagement d'une salle
  d'opération, deux indices avec des écarts volontaires (dont un non signalé au cartouche) ;
- cctp-extrait-lot-salles-propres.pdf / .txt : extrait de CCTP avec des incohérences volontaires ;
- liste-equipements-salle3.csv : liste d'équipements du négoce, avec un écart volontaire ;
- maquette-bloc.ifc : maquette IFC 4 minimale (espaces + jeux de propriétés, sans géométrie).

Usage : python3 generer_documents.py
"""

import subprocess
from pathlib import Path

from reportlab.lib.pagesizes import A3, A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

OUT = Path(__file__).resolve().parent / "documents"
OUT.mkdir(exist_ok=True)

# --------------------------------------------------------------------------- plans

# Échelle 1/75 : 1 m = 13,33 mm sur le papier.
S = 1000 / 75 * mm
OX, OY = 30 * mm, 95 * mm  # origine du dessin (coin bas gauche du bâtiment)


def m(x, y):
    return OX + x * S, OY + y * S


def rect(c, x, y, w, h, fill=None, dash=None, lw=0.6):
    c.setLineWidth(lw)
    if dash:
        c.setDash(*dash)
    if fill:
        c.setFillGray(fill)
    X, Y = m(x, y)
    c.rect(X, Y, w * S, h * S, stroke=1, fill=1 if fill else 0)
    c.setDash()
    c.setFillGray(0)


def text(c, x, y, s, size=7, bold=False, centre=False):
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    X, Y = m(x, y)
    (c.drawCentredString if centre else c.drawString)(X, Y, s)


def repere(c, x, y, code):
    X, Y = m(x, y)
    c.setLineWidth(0.5)
    c.circle(X, Y, 3.2 * mm, stroke=1, fill=0)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawCentredString(X, Y - 2.2, code)


def plan(indice):
    b = indice == "B"
    path = OUT / f"plan-salle3-ind{indice}.pdf"
    c = canvas.Canvas(str(path), pagesize=landscape(A3))
    W, H = landscape(A3)
    c.setTitle(f"CHV-BLOC-PLA-S3 indice {indice}")

    # Cadre
    c.setLineWidth(1)
    c.rect(10 * mm, 10 * mm, W - 20 * mm, H - 20 * mm)

    # Murs : salle d'opération 3 (7,0 x 6,6 m), SAS (2,6 x 3,0), préparation (2,6 x 3,6),
    # arsenal stérile (3,2 x 3,0), couloir propre (largeur 2,4).
    rect(c, 0, 0, 13.2, 9.0, lw=2.2)  # enveloppe
    rect(c, 0, 0, 7.0, 6.6, lw=1.6)  # salle 3
    rect(c, 7.0, 3.6, 2.6, 3.0, lw=1.2)  # SAS
    rect(c, 7.0, 0, 2.6, 3.6, lw=1.2)  # préparation
    rect(c, 9.6, 0, 3.6, 3.0, lw=1.2)  # arsenal
    rect(c, 0, 6.6, 13.2, 2.4, lw=1.2, fill=0.94)  # couloir propre

    text(c, 3.5, 6.1, "SALLE D'OPÉRATION 3", 9, True, True)
    text(c, 3.5, 5.75, "Surface : 46,2 m²  -  Classe ISO 5 (zone opératoire)", 6.5, False, True)
    text(c, 8.3, 5.9, "SAS PATIENT", 7, True, True)
    text(c, 8.3, 2.9, "SALLE DE", 7, True, True)
    text(c, 8.3, 2.6, "PRÉPARATION", 7, True, True)
    text(c, 11.4, 1.4, "ARSENAL STÉRILE", 7, True, True)
    text(c, 11.4, 4.8, "LOCAL TECHNIQUE", 7, True, True)
    text(c, 6.6, 7.75, "COULOIR PROPRE", 8, True, True)

    # Portes (repère + largeur de passage, notée en texte)
    largeur_p3 = "1,20" if b else "1,40"
    portes = [
        (7.0, 4.4, "P1", "Porte coulissante hermétique 1,40 x 2,10"),
        (7.0, 1.2, "P2", "Porte va-et-vient 0,90 x 2,10"),
        (2.6, 6.6, "P3", f"Porte coulissante hermétique {largeur_p3} x 2,10"),
        (9.6, 1.0, "P4", "Porte battante 0,90 x 2,10"),
    ]
    for x, y, code, lib in portes:
        X, Y = m(x, y)
        c.setFillGray(1)
        c.rect(X - 2.2 * mm, Y - 2.2 * mm, 4.4 * mm, 4.4 * mm, stroke=1, fill=1)
        c.setFillGray(0)
        c.setFont("Helvetica-Bold", 6)
        c.drawCentredString(X, Y - 2, code)

    # Plafond soufflant (zone pointillée)
    ps = 2.8 if b else 3.2
    x0, y0 = 3.5 - ps / 2, 3.2 - ps / 2
    rect(c, x0, y0, ps, ps, dash=(4, 3), lw=0.8)
    text(c, x0 + 0.1, y0 + ps + 0.12, f"Plafond soufflant {str(ps).replace('.', ',')} x {str(ps).replace('.', ',')} m - flux unidirectionnel", 6)

    # Équipements (repères)
    rect(c, 2.6, 2.95, 1.8, 0.5, fill=0.85)  # table
    repere(c, 3.5, 3.2, "E04")  # table d'opération
    repere(c, 3.5, 4.25, "E03")  # scialytique
    repere(c, 1.4, 4.6, "E01")  # bras anesthésie
    if b:
        repere(c, 5.7, 1.4, "E02")  # bras chirurgien déplacé
    else:
        repere(c, 5.6, 4.6, "E02")
    repere(c, 0.45, 1.0, "E06")  # tableau de commande
    repere(c, 6.55, 3.2, "E07")  # écran mural
    repere(c, 0.45, 5.6, "E08")  # prises fluides médicaux (murale)
    if b:
        repere(c, 4.6, 0.45, "E09")  # pupitre informatique ajouté en indice B
    repere(c, 8.3, 4.8, "E10")  # lave-mains chirurgical (dans le SAS)

    # Nord + échelle
    X, Y = m(12.4, 8.5)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(X, Y + 12, "N")
    c.line(X, Y - 8, X, Y + 8)
    X, Y = m(0, -1.2)
    c.setLineWidth(1)
    c.line(X, Y, X + 5 * S, Y)
    for i in range(6):
        c.line(X + i * S, Y - 2, X + i * S, Y + 2)
    c.setFont("Helvetica", 6.5)
    c.drawString(X, Y + 5, "0")
    c.drawString(X + 5 * S - 6, Y + 5, "5 m")
    c.drawString(X + 5 * S + 10, Y - 2, "Échelle 1/75 (format A3)")

    # Nomenclature
    nomen = [
        ("E01", "Bras plafonnier anesthésie, 2 étagères", "1"),
        ("E02", "Bras plafonnier chirurgien, 1 étagère", "1"),
        ("E03", "Scialytique double coupole LED", "1"),
        ("E04", "Table d'opération mobile", "1"),
        ("E06", "Tableau de commande de salle (ambiance, gaz)", "1"),
        ("E07", "Écran mural 55 pouces", "1"),
        ("E08", "Prises fluides médicaux murales (O2, AIR, VIDE)", "3"),
        ("E10", "Lave-mains chirurgical 2 postes", "1"),
    ]
    if b:
        nomen.insert(6, ("E09", "Pupitre informatique mural", "1"))
    tx, ty = W - 160 * mm, H - 22 * mm
    c.setFont("Helvetica-Bold", 8)
    c.drawString(tx, ty, "NOMENCLATURE DES ÉQUIPEMENTS - SALLE 3")
    c.setFont("Helvetica-Bold", 6.5)
    ty -= 7 * mm
    c.drawString(tx, ty, "Repère")
    c.drawString(tx + 16 * mm, ty, "Désignation")
    c.drawString(tx + 120 * mm, ty, "Qté")
    c.setFont("Helvetica", 6.5)
    for code, lib, q in nomen:
        ty -= 5 * mm
        c.drawString(tx, ty, code)
        c.drawString(tx + 16 * mm, ty, lib)
        c.drawString(tx + 120 * mm, ty, q)
    ty -= 9 * mm
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(tx, ty, "PORTES")
    c.setFont("Helvetica", 6.5)
    for x, y, code, lib in portes:
        ty -= 5 * mm
        c.drawString(tx, ty, code)
        c.drawString(tx + 16 * mm, ty, lib)

    # Cartouche
    cx, cy, cw, ch = W - 160 * mm, 10 * mm, 150 * mm, 72 * mm
    c.setLineWidth(1)
    c.rect(cx, cy, cw, ch)
    lignes = [
        ("Maître d'ouvrage", "Centre hospitalier de Valmont (fictif)"),
        ("Opération", "Restructuration du bloc opératoire - salles 1 à 4"),
        ("Lot", "Lot 05 - Salles propres et équipements"),
        ("Bureau d'études", "Alpha Ingénierie (fictif)"),
        ("Document", "Plan d'aménagement - Salle d'opération 3"),
        ("N° de plan", "CHV-BLOC-PLA-S3"),
        ("Phase", "DCE"),
        ("Échelle", "1/75"),
    ]
    yy = cy + ch - 6 * mm
    for k, v in lignes:
        c.setFont("Helvetica-Bold", 7)
        c.drawString(cx + 3 * mm, yy, k)
        c.setFont("Helvetica", 7)
        c.drawString(cx + 38 * mm, yy, v)
        yy -= 5.5 * mm
    # Tableau des indices
    c.line(cx, cy + 17 * mm, cx + cw, cy + 17 * mm)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(cx + 3 * mm, cy + 12 * mm, "Ind.")
    c.drawString(cx + 14 * mm, cy + 12 * mm, "Date")
    c.drawString(cx + 36 * mm, cy + 12 * mm, "Modification")
    c.setFont("Helvetica", 6.5)
    c.drawString(cx + 3 * mm, cy + 8 * mm, "A")
    c.drawString(cx + 14 * mm, cy + 8 * mm, "03/11/2026")
    c.drawString(cx + 36 * mm, cy + 8 * mm, "Première diffusion")
    if b:
        c.drawString(cx + 3 * mm, cy + 4 * mm, "B")
        c.drawString(cx + 14 * mm, cy + 4 * mm, "20/11/2026")
        # Volontairement incomplet : la réduction de la porte P3 et du plafond soufflant
        # ne sont pas signalées.
        c.drawString(cx + 36 * mm, cy + 4 * mm,
                     "Déplacement du bras chirurgien E02, ajout du pupitre E09")

    c.showPage()
    c.save()
    png = path.with_suffix("")
    subprocess.run(["pdftoppm", "-png", "-r", "130", "-singlefile", str(path), str(png)],
                   check=True)
    return path


# --------------------------------------------------------------------------- CCTP

CCTP = """CENTRE HOSPITALIER DE VALMONT (fictif)
Restructuration du bloc opératoire - salles 1 à 4
CCTP - Lot 05 - Salles propres et équipements - Extrait (phase DCE)

5.3 SALLE D'OPÉRATION 3

5.3.1 Classement et traitement d'air
La zone opératoire de la salle 3 est classée ISO 5 au repos selon la norme NF S 90-351.
Elle est équipée d'un plafond soufflant à flux unidirectionnel de dimensions minimales
3,20 x 3,20 m, centré sur la table d'opération. La surpression de la salle par rapport
au couloir propre est de 15 Pa minimum. Le taux de brassage est d'au moins 50 volumes/heure.

5.3.2 Menuiseries
La porte d'accès depuis le couloir propre (P3) est une porte coulissante hermétique
automatique, passage libre de 1,40 x 2,10 m minimum, permettant le passage d'un lit.
La porte vers le SAS patient (P1) est identique.

5.3.3 Équipements suspendus
La salle reçoit deux bras plafonniers (anesthésie et chirurgien) et un scialytique double
coupole LED. Le bras chirurgien est positionné côté opposé au bras d'anesthésie par rapport
à la table, à moins de 2,00 m de l'axe de celle-ci.

5.3.4 Fluides médicaux
La salle comporte au minimum quatre prises murales de fluides médicaux (O2, AIR,
VIDE, N2O), en complément des prises équipant les bras plafonniers.

5.3.5 Équipements de communication
Un écran mural de 55 pouces et un pupitre informatique mural sont prévus. Le tableau de
commande de salle regroupe la commande de l'ambiance (température, hygrométrie,
éclairage) et la supervision des gaz.
"""


def cctp():
    (OUT / "cctp-extrait-lot-salles-propres.txt").write_text(CCTP, encoding="utf-8")
    c = canvas.Canvas(str(OUT / "cctp-extrait-lot-salles-propres.pdf"), pagesize=A4)
    W, H = A4
    y = H - 25 * mm
    for i, line in enumerate(CCTP.splitlines()):
        bold = i < 3 or line[:1].isdigit()
        c.setFont("Helvetica-Bold" if bold else "Helvetica", 10 if bold else 9.5)
        c.drawString(22 * mm, y, line)
        y -= 6 * mm if line else 3 * mm
    c.save()


# --------------------------------------------------------------------------- liste équipements

LISTE = """repere;designation;fabricant_reference;quantite;salle
E01;Bras plafonnier anesthésie 2 étagères;Fournisseur X - BPA-200;1;Salle 3
E02;Bras plafonnier chirurgien 1 étagère;Fournisseur X - BPC-100;1;Salle 3
E03;Scialytique double coupole LED;Fournisseur Y - SCIA-LED-2;1;Salle 3
E04;Table d'opération mobile;Fournisseur Z - TOM-500;1;Salle 3
E06;Tableau de commande de salle;Fournisseur W - TCS-12;1;Salle 3
E07;Écran mural 32 pouces;Fournisseur V - EM-32;1;Salle 3
E08;Prise fluide médical murale;Fournisseur U - PFM;4;Salle 3
E10;Lave-mains chirurgical 2 postes;Fournisseur T - LMC-2;1;SAS salle 3
"""


def liste():
    (OUT / "liste-equipements-salle3.csv").write_text(LISTE, encoding="utf-8")


# --------------------------------------------------------------------------- IFC

ESPACES = [
    # nom, libellé, surface, classe ISO, plafond soufflant, surpression Pa, brassage vol/h
    ("SO1", "Salle d'opération 1", 44.8, "ISO 5", True, 15, 50),
    ("SO2", "Salle d'opération 2", 45.5, "ISO 5", False, 15, 50),
    ("SO3", "Salle d'opération 3", 46.2, "ISO 5", True, 15, 50),
    ("SO4", "Salle d'opération 4", 52.0, "ISO 5", True, 10, 50),
    ("SAS3", "SAS patient salle 3", 7.8, "ISO 7", False, 10, 20),
    ("PREP3", "Salle de préparation 3", 9.4, "ISO 7", False, 10, 20),
    ("ARS", "Arsenal stérile", 10.8, "ISO 7", False, 10, 20),
    ("SSPI", "Salle de surveillance post-interventionnelle", 86.0, "ISO 8", False, 5, 15),
    ("CPR", "Couloir propre", 31.7, "ISO 8", False, 5, 15),
]


def ifc():
    lines, n = [], [0]

    def add(s):
        n[0] += 1
        lines.append(f"#{n[0]}={s};")
        return n[0]

    def gid(i):
        # GlobalId IFC : 22 caractères (fictif mais au bon format)
        base = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_$"
        return "".join(base[(i * 7 + k * 13) % 64] for k in range(22))

    person = add("IFCPERSON($,'Alpha','Ingénierie',$,$,$,$,$)".replace("é", "\\X2\\00E9\\X0\\"))
    org = add("IFCORGANIZATION($,'Alpha Ingenierie (fictif)',$,$,$)")
    po = add(f"IFCPERSONANDORGANIZATION(#{person},#{org},$)")
    app = add(f"IFCAPPLICATION(#{org},'1.0','generer_documents.py','demo')")
    oh = add(f"IFCOWNERHISTORY(#{po},#{app},$,.ADDED.,$,$,$,0)")
    u1 = add("IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.)")
    u2 = add("IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.)")
    ua = add(f"IFCUNITASSIGNMENT((#{u1},#{u2}))")
    proj = add(f"IFCPROJECT('{gid(1)}',#{oh},'CH Valmont - Bloc operatoire (fictif)',$,$,$,$,$,#{ua})")
    site = add(f"IFCSITE('{gid(2)}',#{oh},'Site CH Valmont',$,$,$,$,$,.ELEMENT.,$,$,$,$,$)")
    bat = add(f"IFCBUILDING('{gid(3)}',#{oh},'Batiment B - Plateau technique',$,$,$,$,$,.ELEMENT.,$,$,$)")
    niv = add(f"IFCBUILDINGSTOREY('{gid(4)}',#{oh},'Niveau 1 - Bloc operatoire',$,$,$,$,$,.ELEMENT.,4.2)")
    add(f"IFCRELAGGREGATES('{gid(5)}',#{oh},$,$,#{proj},(#{site}))")
    add(f"IFCRELAGGREGATES('{gid(6)}',#{oh},$,$,#{site},(#{bat}))")
    add(f"IFCRELAGGREGATES('{gid(7)}',#{oh},$,$,#{bat},(#{niv}))")

    def enc(s):
        return "".join(c if ord(c) < 128 else f"\\X2\\{ord(c):04X}\\X0\\" for c in s).replace("'", "''")

    spaces = []
    for i, (code, lib, surf, iso, ps, pa, br) in enumerate(ESPACES):
        sp = add(f"IFCSPACE('{gid(100 + i)}',#{oh},'{code}','{enc(lib)}',$,$,$,'{enc(lib)}',"
                 f".ELEMENT.,.INTERNAL.,$)")
        spaces.append(sp)
        p1 = add(f"IFCPROPERTYSINGLEVALUE('NetFloorArea',$,IFCAREAMEASURE({surf}),$)")
        q = add(f"IFCPROPERTYSET('{gid(200 + i)}',#{oh},'Pset_SpaceCommon',$,(#{p1}))")
        add(f"IFCRELDEFINESBYPROPERTIES('{gid(300 + i)}',#{oh},$,$,(#{sp}),#{q})")
        v = ".T." if ps else ".F."
        a = add(f"IFCPROPERTYSINGLEVALUE('ClasseISO',$,IFCLABEL('{iso}'),$)")
        b_ = add(f"IFCPROPERTYSINGLEVALUE('PlafondSoufflant',$,IFCBOOLEAN({v}),$)")
        c_ = add(f"IFCPROPERTYSINGLEVALUE('SurpressionPa',$,IFCREAL({float(pa)}),$)")
        d = add(f"IFCPROPERTYSINGLEVALUE('TauxBrassageVolH',$,IFCREAL({float(br)}),$)")
        q2 = add(f"IFCPROPERTYSET('{gid(400 + i)}',#{oh},'Pset_SallePropre',$,(#{a},#{b_},#{c_},#{d}))")
        add(f"IFCRELDEFINESBYPROPERTIES('{gid(500 + i)}',#{oh},$,$,(#{sp}),#{q2})")
    add(f"IFCRELAGGREGATES('{gid(8)}',#{oh},$,$,#{niv},({','.join('#' + str(s) for s in spaces)}))")

    head = ("ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('ViewDefinition [ReferenceView]'),'2;1');\n"
            "FILE_NAME('maquette-bloc.ifc','2026-11-24T00:00:00',('Alpha Ingenierie'),"
            "('fictif'),'generer_documents.py','demo','');\nFILE_SCHEMA(('IFC4'));\nENDSEC;\nDATA;\n")
    (OUT / "maquette-bloc.ifc").write_text(head + "\n".join(lines) + "\nENDSEC;\nEND-ISO-10303-21;\n",
                                          encoding="ascii")


if __name__ == "__main__":
    plan("A")
    plan("B")
    cctp()
    liste()
    ifc()
    for p in sorted(OUT.iterdir()):
        print(p.name, p.stat().st_size)
