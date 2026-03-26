import sqlite3
# Assuming you define DB_FILE = "ecosystem.db" in constants.py
from utils.constants import DB_FILE 

def get_connection():
    """A simple helper so you never have to type the DB name repeatedly."""
    return sqlite3.connect(DB_FILE)

def get_active_partner(user_id: str):
    """Used by almost every command (!learn, !deploy, !catch) to find the lead specimen."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT active_partner FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result and result[0] else None

def get_specimen_data(instance_id: str):
    """Fetches everything about a specific caught specimen."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT cp.pokedex_id, cp.level, cp.happiness, s.name, 
               cp.move_1, cp.move_2, cp.move_3, cp.move_4
        FROM caught_pokemon cp
        JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
        WHERE cp.instance_id = ?
    """, (instance_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def check_evolution_trigger(pokedex_id, level, happiness, time_of_day):
    """The central rulebook for biological metamorphosis."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT er.evolved_species_id, s.name 
        FROM evolution_rules er
        JOIN base_pokemon_species s ON er.evolved_species_id = s.pokedex_id
        WHERE er.base_species_id = ? 
        AND er.trigger_name = 'level-up' 
        AND (er.min_level IS NULL OR er.min_level <= ?)
        AND (er.min_happiness IS NULL OR er.min_happiness <= ?)
        AND (er.time_of_day IS NULL OR er.time_of_day = '' OR er.time_of_day = ?)
        ORDER BY er.min_happiness DESC, er.min_level DESC LIMIT 1
    """, (pokedex_id, level, happiness, time_of_day))
    result = cursor.fetchone()
    conn.close()
    return result