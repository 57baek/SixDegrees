-- profiles, posts, likes, comments, friend_requests, reports are owned by the
-- DB/frontend team and live in the private schema. Do not create them here.
--
-- The backend reads profiles via a public view + writable INSTEAD OF trigger:

CREATE OR REPLACE VIEW public.profiles AS
SELECT id, nickname, bio, avatar_url, age, city, state,
       education, occupation, industry, interests, languages,
       profile_tier, is_admin, timezone, is_onboarded, created_at
FROM private.profiles;

CREATE OR REPLACE FUNCTION public.profiles_view_upsert()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO private.profiles (
    id, nickname, bio, avatar_url, age, city, state,
    education, occupation, industry, interests, languages,
    profile_tier, is_admin, timezone
  )
  VALUES (
    NEW.id, NEW.nickname, NEW.bio, NEW.avatar_url, NEW.age,
    NEW.city, NEW.state, NEW.education, NEW.occupation, NEW.industry,
    NEW.interests, NEW.languages,
    COALESCE(NEW.profile_tier, 6),
    COALESCE(NEW.is_admin, false),
    COALESCE(NEW.timezone, 'UTC')
  )
  ON CONFLICT (id) DO UPDATE SET
    nickname     = EXCLUDED.nickname,
    bio          = EXCLUDED.bio,
    avatar_url   = EXCLUDED.avatar_url,
    age          = EXCLUDED.age,
    city         = EXCLUDED.city,
    state        = EXCLUDED.state,
    education    = EXCLUDED.education,
    occupation   = EXCLUDED.occupation,
    industry     = EXCLUDED.industry,
    interests    = EXCLUDED.interests,
    languages    = EXCLUDED.languages,
    profile_tier = EXCLUDED.profile_tier,
    is_admin     = EXCLUDED.is_admin,
    timezone     = EXCLUDED.timezone;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE TRIGGER profiles_view_insert_trigger
INSTEAD OF INSERT ON public.profiles
FOR EACH ROW EXECUTE FUNCTION public.profiles_view_upsert();

-- interactions: public table with FKs to private.profiles
CREATE TABLE interactions (
  user_id_a      UUID NOT NULL REFERENCES private.profiles(id) ON DELETE CASCADE,
  user_id_b      UUID NOT NULL REFERENCES private.profiles(id) ON DELETE CASCADE,
  likes_count    INTEGER DEFAULT 0,
  comments_count INTEGER DEFAULT 0,
  dm_count       INTEGER DEFAULT 0,
  last_updated   TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (user_id_a, user_id_b),
  CHECK (user_id_a < user_id_b)
);

-- backend-owned tables
CREATE TABLE user_positions (
  user_id     UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  x           FLOAT NOT NULL,
  y           FLOAT NOT NULL,
  computed_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE pipeline_runs (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  status      TEXT NOT NULL CHECK (status IN ('success', 'failed', 'skipped')),
  user_count  INTEGER,
  edge_count  INTEGER,
  duration_ms INTEGER,
  error       TEXT,
  created_at  TIMESTAMPTZ DEFAULT now()
);
