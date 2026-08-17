"""Normalises species names on deposits already sitting on the GTS.

The deposit form used to store whatever a player typed, `.capitalize()`d. The matching
engine compares two stored strings, so a deposit reading "Mr. Mime" could never meet a
database that spells it `mr-mime` - it was accepted, listed, and silently unmatchable.

New deposits are stored canonically. This repairs the ones already out there, and
reports any it cannot resolve rather than guessing: a name nobody can identify is
better withdrawn by its owner than quietly rewritten into a different Pokemon.

Safe to run more than once - an already-canonical name resolves to itself.

    python migrate_gts_species.py
"""
import asyncio

import aiosqlite

from utils.constants import DB_FILE
from utils.species import resolve_species, suggest_species


async def run_migration():
    async with aiosqlite.connect(DB_FILE) as db:
        print(f"=== GTS SPECIES NORMALISATION on {DB_FILE} ===")

        async with db.execute(
                "SELECT gts_id, user_id, dep_species, req_species FROM gts_deposits") as cursor:
            deposits = await cursor.fetchall()

        if not deposits:
            print("No GTS deposits to check.")
            return

        changed, already, unresolved = 0, 0, []

        for gts_id, user_id, dep_species, req_species in deposits:
            dep_fixed = resolve_species(dep_species)
            req_fixed = resolve_species(req_species)

            if dep_fixed is None or req_fixed is None:
                unresolved.append((gts_id, user_id, dep_species, req_species,
                                   dep_fixed, req_fixed))
                continue

            if (dep_fixed, req_fixed) == (dep_species, req_species):
                already += 1
                continue

            await db.execute(
                "UPDATE gts_deposits SET dep_species = ?, req_species = ? WHERE gts_id = ?",
                (dep_fixed, req_fixed, gts_id))
            changed += 1
            print(f"  {gts_id}: {dep_species!r} -> {dep_fixed!r}, "
                  f"{req_species!r} -> {req_fixed!r}")

        await db.commit()

        print(f"\n{len(deposits)} deposit(s): {changed} rewritten, "
              f"{already} already canonical, {len(unresolved)} unresolvable.")

        for gts_id, user_id, dep_species, req_species, dep_fixed, req_fixed in unresolved:
            broken = dep_species if dep_fixed is None else req_species
            side = 'offered' if dep_fixed is None else 'requested'
            hint = suggest_species(broken)[:3]
            print(f"  ! {gts_id} (user {user_id}): {side} species {broken!r} "
                  f"matches no known species."
                  + (f" Closest: {hint}" if hint else ""))
        if unresolved:
            print("\nThose are left untouched deliberately - rewriting a name nobody "
                  "can identify would silently change which Pokemon was asked for. "
                  "Their owners should withdraw and re-deposit them.")

        print("Migration complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
