"""Curated prompt templates for script and thumbnail generation."""


def get_prompt_templates() -> list[dict]:
    """Return curated prompt templates organized by category."""
    return [
        # Script templates
        {
            "name": "Dramatisch Sportdocumentaire",
            "category": "script",
            "template": "Schrijf als een HBO sportdocumentaire. Dramatische pauzes, emotionele hoogtepunten, spanning opbouwen naar het climax-moment.",
        },
        {
            "name": "True Crime / Mystery",
            "category": "script",
            "template": "Vertel als een true crime documentaire. Begin met het mysterie, geef stukje bij beetje informatie vrij, eindig met de onthulling.",
        },
        {
            "name": "Historisch Episch",
            "category": "script",
            "template": "Vertel als een historisch epos. Grote gebeurtenissen, heldhaftige momenten, epische muziek-achtige pacing.",
        },
        {
            "name": "Comedy / Luchtig",
            "category": "script",
            "template": "Luchtige, grappige toon. Gebruik humor, ironie en onverwachte wendingen. Houd het entertainend en toegankelijk.",
        },
        {
            "name": "Educatief / Uitleg",
            "category": "script",
            "template": "Helder en educatief. Leg complexe onderwerpen simpel uit met voorbeelden en analogieen. Kurzgesagt-stijl.",
        },
        {
            "name": "Viral Short Hook",
            "category": "script",
            "template": "Start met een schokkende uitspraak of vraag. Maximale emotie in minimale tijd. Elke seconde telt.",
        },
        # Thumbnail templates
        {
            "name": "Shocked Face + Bold Text",
            "category": "thumbnail",
            "template": "Verbaasd gezicht met open mond, grote bold tekst met contrast, felle achtergrondkleur. Klassiek YouTube formaat.",
        },
        {
            "name": "Cinematic Wideshot",
            "category": "thumbnail",
            "template": "Cinematische wide shot, dramatische belichting, filmische kleurgrading. Geen tekst nodig, het beeld vertelt het verhaal.",
        },
        {
            "name": "Before/After Split",
            "category": "thumbnail",
            "template": "Split-screen met voor en na vergelijking. Links donker/slecht, rechts helder/goed. Visueel contrast dat nieuwsgierig maakt.",
        },
        {
            "name": "Minimalistisch Clean",
            "category": "thumbnail",
            "template": "Witte of zwarte achtergrond, 1 centraal element, minimale tekst. Apple-achtige esthetiek. Less is more.",
        },
        # Hook templates
        {
            "name": "Schokkend Feit",
            "category": "hook",
            "template": "Begin met een schokkend statistiek of feit dat niemand verwacht. 'Wist je dat...' maar dan confronterend.",
        },
        {
            "name": "Controversiele Stelling",
            "category": "hook",
            "template": "Open met een controversiele of provocerende stelling waar mensen het mee oneens zijn. Triggert reacties.",
        },
        {
            "name": "Visuele Tease",
            "category": "hook",
            "template": "Toon het meest spectaculaire moment van de video als teaser, dan 'Maar laten we bij het begin beginnen...'",
        },
    ]
