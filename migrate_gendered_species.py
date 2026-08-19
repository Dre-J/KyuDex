"""Makes a species' NAME and its gender_rate agree.

Eleven species entries carry a `-male` or `-female` suffix, and every one of them had a
gender_rate that contradicted it. `gender_rate` is eighths-female, so:

    meowstic-female   rate 4  ->  half of all Meowstic FEMALES were rolled male
    pyroar-male       rate 7  ->  seven in eight "Pyroar Male" were rolled female

Two different faults sit inside that list, and they need opposite fixes.

**Three are not sex-forms at all.** `pyroar-male`, `frillish-male` and `jellicent-male`
are the ONLY entry their species has - there is no `pyroar-female` row anywhere. In the
games the female differs by appearance and nothing else, so PokeAPI's default-form name
leaked in as if it were the species name. Renaming them to the bare species is the fix:
Pyroar really is 87.5% female, and the female sprite already exists on disk, so once the
name stops claiming a sex the existing sprite chain shows the right picture.

**Eight genuinely are sex-forms.** Meowstic, Indeedee, Basculegion and Oinkologne have
two separate entries with different stats and sprites. For those the name is the answer,
so the rate is pinned: 0 (always male) or 8 (always female).

Safe to run more than once - it reports what it changed and does nothing on a second
pass. The engine is corrected independently in utils/formulas.py, so a database that has
not had this run still rolls the sex-forms correctly; what the migration fixes is the
stored data and the three misleading NAMES, which code cannot repair.

    python migrate_gendered_species.py
"""
import asyncio

import aiosqlite

from utils.constants import DB_FILE

# Sole entries for their species, misnamed after PokeAPI's default form.
RENAME = {
    'pyroar-male': 'pyroar',
    'frillish-male': 'frillish',
    'jellicent-male': 'jellicent',
}

# Genuine sex-forms. eighths-female: 0 = always male, 8 = always female.
PIN_RATE = {
    'meowstic-male': 0,     'meowstic-female': 8,
    'indeedee-male': 0,     'indeedee-female': 8,
    'basculegion-male': 0,  'basculegion-female': 8,
    'oinkologne-male': 0,   'oinkologne-female': 8,
}


async def run_migration():
    async with aiosqlite.connect(DB_FILE) as db:
        print(f"=== GENDERED SPECIES MIGRATION on {DB_FILE} ===")

        # ------------------------------------------------------------------
        # 1. The three that should never have carried a sex in their name.
        # ------------------------------------------------------------------
        renamed = 0
        for old, new in RENAME.items():
            async with db.execute(
                    "SELECT pokedex_id FROM base_pokemon_species WHERE name = ?",
                    (old,)) as cursor:
                row = await cursor.fetchone()
            if not row:
                print(f"'{old}' not present (already renamed?). Skipping.")
                continue

            # Refuse rather than collide. If a real `pyroar` row ever appears, renaming
            # onto it would give two species the same name, and every lookup in the bot
            # resolves species BY NAME.
            async with db.execute(
                    "SELECT COUNT(*) FROM base_pokemon_species WHERE name = ?",
                    (new,)) as cursor:
                if (await cursor.fetchone())[0]:
                    print(f"⚠️ '{new}' already exists - leaving '{old}' alone.")
                    continue

            await db.execute(
                "UPDATE base_pokemon_species SET name = ? WHERE name = ?", (new, old))
            # Translations key on the English name, so they move with it.
            await db.execute(
                "UPDATE species_translations SET english_name = ? WHERE english_name = ?",
                (new, old))
            print(f"Renamed '{old}' -> '{new}' (dex {row[0]}).")
            renamed += 1

        # ------------------------------------------------------------------
        # 2. The eight that are real sex-forms: make the rate obey the name.
        # ------------------------------------------------------------------
        pinned = 0
        for name, rate in PIN_RATE.items():
            cursor = await db.execute(
                "UPDATE base_pokemon_species SET gender_rate = ? "
                "WHERE name = ? AND gender_rate IS NOT ?", (rate, name, rate))
            if cursor.rowcount:
                sex = 'always male' if rate == 0 else 'always female'
                print(f"Pinned '{name}' to {sex}.")
                pinned += cursor.rowcount

        # ------------------------------------------------------------------
        # 3. Specimens already caught under a contradicting sex.
        # ------------------------------------------------------------------
        # A Meowstic Female sitting in somebody's box recorded as male is the same
        # contradiction, and it will not fix itself - the sex was written at capture.
        corrected = 0
        for name, rate in PIN_RATE.items():
            wanted = 'M' if rate == 0 else 'F'
            cursor = await db.execute("""
                UPDATE caught_pokemon SET gender = ?
                WHERE gender IS NOT ?
                  AND pokedex_id IN (SELECT pokedex_id FROM base_pokemon_species
                                     WHERE name = ?)
            """, (wanted, wanted, name))
            if cursor.rowcount:
                print(f"Corrected {cursor.rowcount} caught {name} to {wanted}.")
                corrected += cursor.rowcount

        await db.commit()

        # ------------------------------------------------------------------
        # 4. Report what is left, so a bad run is visible rather than assumed.
        # ------------------------------------------------------------------
        async with db.execute(
                "SELECT name, gender_rate FROM base_pokemon_species "
                "WHERE name LIKE '%-male' OR name LIKE '%-female' ORDER BY name") as cursor:
            remaining = await cursor.fetchall()

        disagreeing = [
            (n, r) for n, r in remaining
            if (n.endswith('-male') and (r or 4) != 0)
            or (n.endswith('-female') and (r or 4) != 8)
        ]

        print()
        print(f"{renamed} renamed, {pinned} rate(s) pinned, "
              f"{corrected} caught specimen(s) corrected.")
        print(f"{len(remaining)} sex-named species remain; "
              f"{len(disagreeing)} still disagree with their name.")
        for name, rate in disagreeing:
            print(f"   ⚠️ {name} (rate {rate})")
        print("Migration complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
