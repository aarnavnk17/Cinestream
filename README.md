# CineStream - Premium Movie Rental System

A high-end, full-stack movie rental platform built with **Python/Flask**, featuring a fully normalized **3NF/BCNF database schema**, automated **TMDB API integration**, and a professional **Amethyst & Midnight** UI design.

---

## 1. Introduction
CineStream is a modern web application designed to simulate a digital movie rental experience. It allows users to browse a vast catalog of movies, filter by language and genre, and rent titles for various durations (2 Days, 1 Week, 1 Month). The system is built with a focus on database integrity, performance, and premium user experience.

## 2. Problem Statement
Traditional movie rental systems often suffer from:
*   **Redundant Data**: Duplicate entries for genres and languages.
*   **Schema Rigidity**: Difficulty in updating pricing across large catalogs.
*   **Poor Discovery**: Lack of automated data synchronization with global movie databases.
*   **Subpar UI**: Generic designs that don't feel "premium" or modern.

CineStream solves these by implementing a normalized relational database and an automated sync engine.

## 3. System Requirements

### Functional Requirements
*   **User Management**: Secure registration and login with hashed passwords.
*   **Automated Catalog**: Integration with TMDB API to fetch real-world movie data (posters, descriptions, ratings).
*   **Dynamic Pricing**: Tiered pricing based on the movie's release year (Premium, Recent, Modern, Vintage).
*   **Shopping Cart**: Multiple-item checkout with dynamic price calculation.
*   **Admin Dashboard**: Inventory management, database exploration, and manual sync triggers.

### Non-Functional Requirements
*   **Security**: Use of `werkzeug` for secure password hashing.
*   **Performance**: Optimized SQL queries with table joins to ensure fast page loads.
*   **Aesthetics**: A custom "Amethyst & Midnight" theme using CSS3 and Bootstrap 5.
*   **Scalability**: Normalized schema allows for easy expansion (e.g., adding Actors or Reviews).

## 4. Technology Stack
*   **Backend**: Python 3, Flask Web Framework.
*   **Database**: SQLite (SQLAlchemy ORM).
*   **Frontend**: HTML5, Vanilla CSS3 (Custom Design System), JavaScript (ES6+), Bootstrap 5.
*   **API**: The Movie Database (TMDB) API for automated content synchronization.

## 5. Normalization Logic (DBMS Achievement)
The database has been meticulously refactored to achieve **Third Normal Form (3NF)** and **Boyce-Codd Normal Form (BCNF)**:

### ✅ BCNF (Boyce-Codd Normal Form)
We have extracted all repeating groups and descriptive attributes into separate lookup tables. Every determinant is a candidate key.
*   **Languages Table**: Extracted from Movie strings to a dedicated `Language` table.
*   **Genres Table**: Implemented as a Many-to-Many relationship with `Movie` via the `movie_genres` junction table.
*   **PricingTiers Table**: Centralized pricing logic to prevent update anomalies.

### ✅ 3NF (Third Normal Form)
We have eliminated all transitive dependencies.
*   **Dynamic Cost Calculation**: The `CartItem` table no longer stores a `cost` attribute. Instead, the cost is calculated dynamically at the application level based on the `PricingTier` and `duration`. This ensures that a change in a movie's price tier immediately reflects in all active carts without needing to update multiple records.
*   **Historical Snapshots**: The `Rental` table stores a `cost` as a snapshot. While `Rental.id -> Movie.id -> Price` might look like a transitive dependency, in financial systems, this is a **Data Snapshot** pattern used to preserve historical transaction integrity (so past rentals don't change if prices rise today).

## 6. Relational Model
*   **Users**(id, username, password, is_admin)
*   **Movies**(id, title, description, image_url, release_year, language_id, tier_id, available)
*   **Languages**(id, name, code)
*   **Genres**(id, name)
*   **PricingTiers**(id, name, price, description)
*   **MovieGenres**(movie_id, genre_id) [Junction Table]
*   **Rentals**(id, user_id, movie_id, cost, duration, rental_date, returned)

## 7. Implementation Highlights
*   **Safe JS Details**: Used HTML5 `data-*` attributes to pass movie data to the UI, preventing crashes from special characters.
*   **Auto-Sync**: The app automatically detects a fresh deployment and triggers the TMDB sync engine.
*   **Amethyst Theme**: A professional UI built with deep midnight purples and vibrant magentas.

---

