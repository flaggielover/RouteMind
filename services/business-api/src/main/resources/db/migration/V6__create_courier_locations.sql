CREATE TABLE routemind.courier_locations (
    courier_id UUID PRIMARY KEY,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    observed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT ck_courier_latitude CHECK (latitude >= -90 AND latitude <= 90),
    CONSTRAINT ck_courier_longitude CHECK (longitude >= -180 AND longitude <= 180)
);

COMMENT ON TABLE routemind.courier_locations IS
    'Durable courier location source for rebuildable Redis GEO projection';
