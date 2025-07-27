import os
import time
import json
import random
import signal
import threading
from datetime import datetime, timedelta

import requests
import psycopg2
from faker import Faker
from kafka import KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import TopicAlreadyExistsError, UnknownTopicOrPartitionError

# --- Configuration ---
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
SCHEMA_REGISTRY_URL = "http://localhost:8085"
TOPICS_TO_RESET = ["users", "posts", "comments"]
CONNECT_API_URL = "http://localhost:8083/connectors"
SOURCE_CONNECTOR_NAME = "source-connector"
SINK_CONNECTOR_NAME = "sink-connector"
SOURCE_CONFIG_PATH = "kafka-4/cdc/schema-registry-connector/source_connector.json"
SINK_CONFIG_PATH = "kafka-4/cdc/schema-registry-connector/sink_connector.json"
SOURCE_DB_CONFIG = {
    "dbname": "source_db",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
    "port": "5442",
}

SINK_DB_CONFIG = {
    "dbname": "sink_db",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
    "port": "5443",
}

START_DATE = datetime(2023, 1, 1)
ACTION_INTERVAL_SECONDS = 1 # 메인 루프의 실행 간격

INITIAL_USERS = 50
INITIAL_POSTS_PER_USER = 3
INITIAL_COMMENTS_PER_POST = 2

# --- Global State ---
fake = Faker()
current_time = START_DATE

# In-memory store for created IDs to maintain relationships
user_ids = []
post_ids = []
comment_ids = []

# --- Time Management ---
def get_now():
    """Returns the current simulated time."""
    global current_time
    current_time += timedelta(seconds=random.randint(10, 60))
    return current_time

# --- Kafka Topic Management ---
def reset_kafka_topics(shutdown_event):
    """Deletes and recreates Kafka topics, checking for shutdown signal."""
    print("\n--- Resetting Kafka Topics ---")
    try:
        admin_client = KafkaAdminClient(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            client_id='cdc-generator'
        )
        
        # 1. Delete topics if they exist
        print(f"Attempting to delete topics: {TOPICS_TO_RESET}...")
        try:
            admin_client.delete_topics(topics=TOPICS_TO_RESET, timeout_ms=5000)
            
            # 2. Poll until topics are actually gone
            print("Waiting for topics to be fully removed...")
            start_time = time.time()
            while not shutdown_event.is_set():
                existing_topics = admin_client.list_topics()
                topics_still_exist = [t for t in TOPICS_TO_RESET if t in existing_topics]
                
                if not topics_still_exist:
                    print("All target topics have been removed.")
                    break
                
                if time.time() - start_time > 30: # 30 second timeout
                    print(f"ERROR: Timeout waiting for topics to be deleted. Topics remaining: {topics_still_exist}")
                    admin_client.close()
                    return False

                print(f"Waiting for deletion of: {topics_still_exist}...")
                # Use event.wait for a non-blocking sleep that respects shutdown
                if shutdown_event.wait(1):
                    print("Shutdown requested during topic deletion.")
                    break

        except UnknownTopicOrPartitionError:
            print("Topics did not exist initially, which is fine.")
        except Exception as e:
            print(f"An error occurred during topic deletion (will proceed to creation): {e}")

        # 3. Recreate topics
        print(f"Recreating topics: {TOPICS_TO_RESET}...")
        new_topics = [NewTopic(name=topic, num_partitions=1, replication_factor=1) for topic in TOPICS_TO_RESET]
        try:
            admin_client.create_topics(new_topics=new_topics, validate_only=False)
        except TopicAlreadyExistsError:
            # This can happen in a race condition. If they exist, our goal is met.
            print("Topics already existed, which is acceptable. Proceeding...")
        
        admin_client.close()
        print("--- Kafka Topics Reset Complete ---\n")
        return True

    except Exception as e:
        print(f"FATAL: Could not complete Kafka topic reset: {e}")
        return False

# --- Schema Registry Management ---
def reset_schema_registry_subjects():
    """Deletes all schema versions for the given topics."""
    print("\n--- Resetting Schema Registry Subjects ---")
    subjects_to_delete = [f"{topic}-key" for topic in TOPICS_TO_RESET] + [f"{topic}-value" for topic in TOPICS_TO_RESET]
    
    all_cleared = True
    for subject in subjects_to_delete:
        url = f"{SCHEMA_REGISTRY_URL}/subjects/{subject}"
        try:
            # Note: This deletes the subject and all its versions.
            response = requests.delete(url)
            if response.status_code == 200:
                print(f"Successfully deleted subject '{subject}'.")
            elif response.status_code == 404:
                print(f"Subject '{subject}' not found, skipping.")
            else:
                print(f"Failed to delete subject '{subject}'. Status: {response.status_code}, Response: {response.text}")
                all_cleared = False
        except requests.exceptions.ConnectionError as e:
            print(f"ERROR: Could not connect to Schema Registry at {SCHEMA_REGISTRY_URL}.")
            return False

    if all_cleared:
        print("--- Schema Registry Reset Complete ---\n")
    return all_cleared

# --- Connector Management ---
def delete_connectors():
    """Deletes the source and sink connectors."""
    print("\n--- Deleting Kafka Connectors ---")
    all_deleted = True
    for name in [SINK_CONNECTOR_NAME, SOURCE_CONNECTOR_NAME]:
        url = f"{CONNECT_API_URL}/{name}"
        try:
            response = requests.delete(url)
            if response.status_code == 204:
                print(f"Successfully deleted connector '{name}'.")
            elif response.status_code == 404:
                print(f"Connector '{name}' not found, skipping.")
            else:
                print(f"Failed to delete connector '{name}'. Status: {response.status_code}, Response: {response.text}")
                all_deleted = False
        except requests.exceptions.ConnectionError as e:
            print(f"ERROR: Could not connect to Kafka Connect API at {CONNECT_API_URL}. Please ensure it's running.")
            return False
    
    if all_deleted:
        print("--- Connector Deletion Complete ---\n")
        time.sleep(3) # Give connect time to settle
    return all_deleted

def create_connectors():
    """Creates new connectors from config files."""
    print("\n--- Creating Kafka Connectors ---")
    connectors_to_create = {
        SOURCE_CONNECTOR_NAME: get_connector_config(SOURCE_CONFIG_PATH),
        SINK_CONNECTOR_NAME: get_connector_config(SINK_CONFIG_PATH),
    }

    for name, config in connectors_to_create.items():
        if config is None:
            return False # Exit if config is missing
        
        create_payload = {
            "name": name,
            "config": config
        }
        
        try:
            response = requests.post(CONNECT_API_URL, headers={"Content-Type": "application/json"}, data=json.dumps(create_payload))
            if response.status_code == 201:
                print(f"Successfully created connector '{name}'.")
            else:
                print(f"Failed to create connector '{name}'. Status: {response.status_code}, Response: {response.text}")
                return False
        except requests.exceptions.ConnectionError:
            print(f"ERROR: Could not connect to Kafka Connect API to create '{name}'.")
            return False
    
    print("--- Connector Creation Complete ---\n")
    return True

# --- Data Population ---
def populate_initial_data(conn):
    """Populates the source database with a batch of initial records."""
    print("\n--- Populating Initial Data ---")
    
    # Temporarily disable random time intervals for faster batch insert
    original_get_now = get_now
    
    # A simple closure to advance time linearly for initial population
    def fast_forward_now():
        global current_time
        current_time += timedelta(minutes=1)
        return current_time
    
    # Ugly but effective way to swap the function
    globals()['get_now'] = fast_forward_now

    try:
        print(f"Creating {INITIAL_USERS} initial users...")
        for _ in range(INITIAL_USERS):
            create_user(conn)

        print(f"Creating initial posts...")
        for user_id in user_ids:
            for _ in range(random.randint(1, INITIAL_POSTS_PER_USER)):
                # Hack to pass a specific user_id to create_post if needed,
                # but random choice is fine for initial data.
                create_post(conn)

        print(f"Creating initial comments...")
        for post_id in post_ids:
            for _ in range(random.randint(1, INITIAL_COMMENTS_PER_POST)):
                create_comment(conn)

        print(f"--- Initial Data Population Complete. Total: {len(user_ids)} users, {len(post_ids)} posts, {len(comment_ids)} comments. ---\n")

    finally:
        # Restore the original get_now function
        globals()['get_now'] = original_get_now

# --- Connector Management ---
def get_connector_config(path):
    """Loads a connector configuration file."""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: Connector config file not found at {path}")
        return None
    except json.JSONDecodeError:
        print(f"ERROR: Could not decode JSON from {path}")
        return None

# --- Database Setup ---
def setup_database(conn):
    """Drops existing tables and creates new ones."""
    with conn.cursor() as cur:
        print("Dropping existing tables...")
        cur.execute("DROP TABLE IF EXISTS comments, posts, users CASCADE;")

        print("Creating 'users' table...")
        cur.execute("""
            CREATE TABLE users (
                user_id SERIAL PRIMARY KEY,
                username VARCHAR(50) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                created_at TIMESTAMP NOT NULL
            );
        """)

        print("Creating 'posts' table...")
        cur.execute("""
            CREATE TABLE posts (
                post_id SERIAL PRIMARY KEY,
                author_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                title VARCHAR(200) NOT NULL,
                content TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            );
        """)

        print("Creating 'comments' table...")
        cur.execute("""
            CREATE TABLE comments (
                comment_id SERIAL PRIMARY KEY,
                post_id INTEGER NOT NULL REFERENCES posts(post_id) ON DELETE CASCADE,
                commenter_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                comment_text VARCHAR(500),
                created_at TIMESTAMP NOT NULL
            );
        """)
        conn.commit()
    print("Database setup complete.")


# --- Action Functions (INSERT, UPDATE, DELETE) ---

def create_user(conn):
    now = get_now()
    with conn.cursor() as cur:
        username = fake.user_name()
        email = fake.email()
        cur.execute(
            "INSERT INTO users (username, email, created_at) VALUES (%s, %s, %s) RETURNING user_id;",
            (username, email, now)
        )
        user_id = cur.fetchone()[0]
        user_ids.append(user_id)
        conn.commit()
        print(f"[{now}] CREATED USER: {username} (ID: {user_id})")

def create_post(conn):
    if not user_ids:
        print("[SKIP] No users exist to create a post.")
        return

    now = get_now()
    author_id = random.choice(user_ids)
    with conn.cursor() as cur:
        title = fake.sentence(nb_words=5)
        content = fake.paragraph(nb_sentences=3)
        cur.execute(
            "INSERT INTO posts (author_id, title, content, created_at, updated_at) VALUES (%s, %s, %s, %s, %s) RETURNING post_id;",
            (author_id, title, content, now, now)
        )
        post_id = cur.fetchone()[0]
        post_ids.append(post_id)
        conn.commit()
        print(f"[{now}] CREATED POST: by user {author_id} (ID: {post_id})")


def create_comment(conn):
    if not user_ids or not post_ids:
        print("[SKIP] Not enough users or posts to create a comment.")
        return
    
    now = get_now()
    post_id = random.choice(post_ids)
    commenter_id = random.choice(user_ids)
    with conn.cursor() as cur:
        comment_text = fake.sentence(nb_words=10)
        cur.execute(
            "INSERT INTO comments (post_id, commenter_id, comment_text, created_at) VALUES (%s, %s, %s, %s) RETURNING comment_id;",
            (post_id, commenter_id, comment_text, now)
        )
        comment_id = cur.fetchone()[0]
        comment_ids.append(comment_id)
        conn.commit()
        print(f"[{now}] CREATED COMMENT: by user {commenter_id} on post {post_id} (ID: {comment_id})")

def update_post(conn):
    if not post_ids:
        print("[SKIP] No posts exist to update.")
        return
    
    now = get_now()
    post_id_to_update = random.choice(post_ids)
    with conn.cursor() as cur:
        new_content = fake.paragraph(nb_sentences=4)
        cur.execute(
            "UPDATE posts SET content = %s, updated_at = %s WHERE post_id = %s;",
            (new_content, now, post_id_to_update)
        )
        conn.commit()
        print(f"[{now}] UPDATED POST: {post_id_to_update}")


def delete_comment(conn):
    if not comment_ids:
        print("[SKIP] No comments exist to delete.")
        return

    comment_id_to_delete = random.choice(comment_ids)
    with conn.cursor() as cur:
        cur.execute("DELETE FROM comments WHERE comment_id = %s;", (comment_id_to_delete,))
        conn.commit()
        comment_ids.remove(comment_id_to_delete)
        print(f"[{get_now()}] DELETED COMMENT: {comment_id_to_delete}")


# --- Verification ---
def verify_sink(source_conn, sink_conn):
    """Compares row counts between source and sink tables."""
    print("\n--- Verifying Sink ---")
    try:
        with source_conn.cursor() as s_cur, sink_conn.cursor() as t_cur:
            for table in ["users", "posts", "comments"]:
                s_cur.execute(f"SELECT COUNT(*) FROM {table};")
                source_count = s_cur.fetchone()[0]
                try:
                    t_cur.execute(f"SELECT COUNT(*) FROM {table};")
                    target_count = t_cur.fetchone()[0]
                    status = "✅" if source_count == target_count else "❌"
                    print(f"[{table.upper()}] Source: {source_count}, Sink: {target_count} {status}")
                except psycopg2.Error as e:
                    print(f"Could not verify table '{table}' in sink. It might not exist yet. Error: {e}")
                    sink_conn.rollback()

    except psycopg2.Error as e:
        print(f"An error occurred during verification: {e}")
    finally:
        print("--- Verification End ---\n")


# --- Main Application ---
def main():
    shutdown_event = threading.Event()

    def handle_shutdown(signum, frame):
        print("\nShutdown signal received. Stopping generator...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    # --- Phase 1: Cleanup (in correct order) ---
    print("===== STARTING PHASE 1: CLEANUP =====")
    # 1. Stop clients
    if not delete_connectors():
        print("Exiting due to connector deletion failure.")
        return
    # 2. Delete schemas
    if not reset_schema_registry_subjects():
        print("Exiting due to Schema Registry reset failure.")
        return
    # 3. Delete data
    if not reset_kafka_topics(shutdown_event):
        print("Exiting due to Kafka topic reset failure.")
        return

    if shutdown_event.is_set(): return

    source_conn = None
    sink_conn = None

    try:
        # --- Phase 2: Staging ---
        print("\n===== STARTING PHASE 2: STAGING =====")
        print("Connecting to source database...")
        source_conn = psycopg2.connect(**SOURCE_DB_CONFIG)
        print("Connecting to sink database...")
        sink_conn = psycopg2.connect(**SINK_DB_CONFIG)
        
        print("\n--- Setting up database schemas ---")
        setup_database(source_conn)
        setup_database(sink_conn)
        print("--- Database schema setup complete ---\n")

        populate_initial_data(source_conn)

        # --- Phase 3: Activation ---
        print("\n===== STARTING PHASE 3: ACTIVATION =====")
        if not create_connectors():
            print("Exiting due to connector creation failure.")
            return
            
        print("Connectors created. Waiting 5 seconds for them to stabilize and start snapshot...")
        time.sleep(5)
        
        print("\n\n--- Starting Real-time Data Generation ---")
        verification_counter = 0
        while not shutdown_event.is_set():
            # Define actions and their weights
            actions = [
                (create_user, 15),
                (create_post, 10),
                (create_comment, 20),
                (update_post, 5),
                (delete_comment, 2),
            ]
            
            action_func, _ = random.choices(actions, weights=[w for _, w in actions], k=1)[0]
            
            try:
                action_func(source_conn)
            except psycopg2.Error as e:
                print(f"Database error occurred: {e}")
                source_conn.rollback() # Rollback on error

            time.sleep(ACTION_INTERVAL_SECONDS)
            
            verification_counter += 1
            if verification_counter >= 20: # Verify every ~10 seconds
                verify_sink(source_conn, sink_conn)
                verification_counter = 0

    except psycopg2.OperationalError as e:
        print(f"Could not connect to the database: {e}")
        print("Please ensure the database containers are running (`docker-compose up -d`).")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if source_conn:
            source_conn.close()
            print("Source database connection closed.")
        if sink_conn:
            sink_conn.close()
            print("Sink database connection closed.")

if __name__ == "__main__":
    main()
