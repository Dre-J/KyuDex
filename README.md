# KyuDex

KyuDex is a discord bot programmed using discord.py designed to bring the Pokémon experience to discord servers. Talk, battle and catch pokemon while you chat with others on the platform. You can also complete field directives and maintain your server's ecosystem health from random pollution events.

## Core Architecture:
KyuDex is built to handle high-volume, concurrent user interactions through a robust, asynchronous Python backend. Rather than a simple command-and-response bot, it functions as a persistent state machine with highly optimized, localized data management.

- **Autonomous Data Pipeline**: To prevent network latency and crashes from third-party outages, the system queries the RESTful PokeAPI only once to ingest static data. This data is extracted, structured, and seeded into a local database, creating a highly stable, closed-loop environment.
- **Relational Data Persistence**: Employs a local SQLite database using ACID protocols to manage user progression, dynamic inventories, and server-wide ecosystem metrics. This ensures data integrity and prevents corruption during asynchronous server events or unexpected restarts.
- **In-Memory State Management (Active Development)**: The algorithmic, turn-based combat system is engineered to run its complex loic entirely in RAM. By managing state in memory rather than continously writing to disk, it drastically reduces I/O operations and enabled rapid calculation of stats, type advantages and dynamic status effects.

## Development Methodology
This application was designed to server as a hands-on technical proving ground for complex state management, relational database design, and asynchronous API integration. During development, I utilized AI-assisted tooling (Google Gemini) to accelerate boilerplate generation, syntax formatting, and documentation. The core system design, database schema design, and final logic implementation were independently designed, directed, and verified.

## 🗺️ Roadmap
The core engine is deployed, but KyuDex is in active development. Immediate priorities focus on finalizing the game logic, while long-term goals involve expanding the environmental simulation aspects.

- [x] Phase 1: Initial Architecture & Database Schema Design.
- [x] Phase 2: PokeAPI Integration & Local Database Seeding.
- [x] Phase 3: Background Ecosystem Health Monitoring Loop.
- [ ] Phase 4 (Current): Finalize In-Memory Turn-Based Combat Logic.
- [ ] Phase 5 (Breeding): A working breeding system with relevant power items.
- [ ] Phase 6: Custom backgrounds and sprites for trainer profiles.
- [ ] Phase 7: Effort Value (EV) missions.

## 🤝 Contributing & Contact
KyuDex is an open-source passion project. Whether you want to help finalize the asynchronous battle loops, expand the ecosystem mechanics, or just optimize the database queries, contributions and pull requests are highly encouraged!

If you are interested in collaborating, reviewing the architecture, or if you have any questions, feel free to reach out directly.

Discord: **shelteredkani or Sollo#4837**
