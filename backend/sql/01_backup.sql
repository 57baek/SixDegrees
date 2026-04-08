-- Step 1: Drop FKs from child tables that reference profiles
ALTER TABLE interactions   DROP CONSTRAINT IF EXISTS interactions_user_id_a_fkey;
ALTER TABLE interactions   DROP CONSTRAINT IF EXISTS interactions_user_id_b_fkey;
ALTER TABLE posts          DROP CONSTRAINT IF EXISTS posts_user_id_fkey;
ALTER TABLE likes          DROP CONSTRAINT IF EXISTS likes_user_id_fkey;
ALTER TABLE comments       DROP CONSTRAINT IF EXISTS comments_user_id_fkey;
ALTER TABLE friend_requests DROP CONSTRAINT IF EXISTS friend_requests_sender_id_fkey;
ALTER TABLE friend_requests DROP CONSTRAINT IF EXISTS friend_requests_receiver_id_fkey;
ALTER TABLE reports        DROP CONSTRAINT IF EXISTS reports_user_id_fkey;

-- Step 2: Drop auth.users FK on profiles itself
ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_id_fkey;

-- Step 3: Rename all tables to _bk
ALTER TABLE profiles        RENAME TO profiles_bk;
ALTER TABLE interactions    RENAME TO interactions_bk;
ALTER TABLE posts           RENAME TO posts_bk;
ALTER TABLE likes           RENAME TO likes_bk;
ALTER TABLE comments        RENAME TO comments_bk;
ALTER TABLE friend_requests RENAME TO friend_requests_bk;
ALTER TABLE reports         RENAME TO reports_bk;

-- Step 4: Rename other tables that may exist
ALTER TABLE IF EXISTS map_coordinates          RENAME TO map_coordinates_bk;
ALTER TABLE IF EXISTS map_coordinates_global   RENAME TO map_coordinates_global_bk;
ALTER TABLE IF EXISTS user_profiles            RENAME TO user_profiles_bk;
ALTER TABLE IF EXISTS pipeline_diagnostics     RENAME TO pipeline_diagnostics_bk;
ALTER TABLE IF EXISTS user_positions           RENAME TO user_positions_bk;
