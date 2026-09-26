from app.database.supabase import supabase

import unicodedata
import re

def normalize_name(value: str) -> str:
    if not value:
        return ""

    value = str(value)
    value = unicodedata.normalize("NFKC", value)

    value = re.sub(
        r"[\u2010\u2011\u2012\u2013\u2014\u2212\uFE58\uFE63\uFF0D]",
        "-",
        value
    )

    value = " ".join(value.strip().lower().split())

    return value

def split_aliases(aliases):
    if not aliases:
        return []

    if isinstance(aliases, list):
        return [
            str(alias).strip()
            for alias in aliases
            if str(alias).strip()
        ]

    aliases = str(aliases)

    if "|" in aliases:
        return [
            alias.strip()
            for alias in aliases.split("|")
            if alias.strip()
        ]
    else:
        return [aliases.strip()] if aliases.strip() else []


def find_ingredient(ingredient: str):
    search_name = normalize_name(ingredient)

    response = (
        supabase
        .table("ingredients")
        .select("*")
        .execute()
    )

    ingredients = response.data or []

    #Match ingredient column (exact match)
    for record in ingredients:
        database_name = normalize_name(
            record.get("ingredient")
        )

        if database_name == search_name:

            return {
                "found": True,
                "matched_by": "ingredient",
                "matched_name": record.get("ingredient"),
                "data": record
            }

    #Match canonical_name column (exact match)
    for record in ingredients:
        canonical_name = normalize_name(
            record.get("canonical_name")
        )

        if canonical_name and canonical_name == search_name:

            return {
                "found": True,
                "matched_by": "canonical_name",
                "matched_name": record.get("canonical_name"),
                "data": record
            }

    #Match aliases column (exact match)
    for record in ingredients:
        aliases = split_aliases(
            record.get("aliases")
        )

        for alias in aliases:
            if normalize_name(alias) == search_name:
                return {
                    "found": True,
                    "matched_by": "alias",
                    "matched_name": alias,
                    "data": record
                }

    #Match ingredient column (partial)
    for record in ingredients:
        database_name = normalize_name(
            record.get("ingredient")
        )

        if search_name in database_name or database_name in search_name:
            return {
                "found": True,
                "matched_by": "ingredient_partial",
                "matched_name": record.get("ingredient"),
                "data": record
            }

    #Match canonical_name column (partial)
    for record in ingredients:
        canonical_name = normalize_name(
            record.get("canonical_name")
        )

        if canonical_name and (search_name in canonical_name or canonical_name in search_name):
            return {
                "found": True,
                "matched_by": "canonical_name_partial",
                "matched_name": record.get("canonical_name"),
                "data": record
            }

    #Match aliases column (partial)
    for record in ingredients:
        aliases = split_aliases(
            record.get("aliases")
        )

        for alias in aliases:
            alias_normalized = normalize_name(alias)
            if search_name in alias_normalized or alias_normalized in search_name:
                return {
                    "found": True,
                    "matched_by": "alias_partial",
                    "matched_name": alias,
                    "data": record
                }

    return {
        "found": False,
        "matched_by": None,
        "matched_name": None,
        "data": None
    }