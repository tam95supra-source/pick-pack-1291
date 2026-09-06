-- R5 QUOTA-REALTIME-DELTA-001
-- Small canonical revision projection. The one-time backfill may scan events;
-- normal sync-status must never scan/group events again.
CREATE TABLE IF NOT EXISTS day_revision_state (
  business_date TEXT NOT NULL,
  authority_epoch INTEGER NOT NULL,
  service_generation TEXT NOT NULL,
  revision INTEGER NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (business_date, authority_epoch, service_generation)
);

INSERT INTO day_revision_state(business_date,authority_epoch,service_generation,revision,updated_at)
SELECT business_date,authority_epoch,service_generation,MAX(authority_seq),MAX(committed_at)
FROM events
GROUP BY business_date,authority_epoch,service_generation
ON CONFLICT(business_date,authority_epoch,service_generation) DO UPDATE SET
  revision=CASE WHEN excluded.revision>day_revision_state.revision THEN excluded.revision ELSE day_revision_state.revision END,
  updated_at=CASE WHEN excluded.revision>=day_revision_state.revision THEN excluded.updated_at ELSE day_revision_state.updated_at END;

CREATE TRIGGER IF NOT EXISTS trg_events_day_revision
AFTER INSERT ON events
BEGIN
  INSERT INTO day_revision_state(business_date,authority_epoch,service_generation,revision,updated_at)
  VALUES(NEW.business_date,NEW.authority_epoch,NEW.service_generation,NEW.authority_seq,NEW.committed_at)
  ON CONFLICT(business_date,authority_epoch,service_generation) DO UPDATE SET
    revision=CASE WHEN excluded.revision>day_revision_state.revision THEN excluded.revision ELSE day_revision_state.revision END,
    updated_at=CASE WHEN excluded.revision>=day_revision_state.revision THEN excluded.updated_at ELSE day_revision_state.updated_at END;
END;
