INSERT INTO weather_requests (
  original_location,
  normalized_location,
  latitude,
  longitude,
  timezone,
  start_date,
  end_date,
  current_weather,
  daily_weather,
  map_data,
  notes
) VALUES
(
  'Montreal',
  'Montreal, Urban agglomeration of Montreal, Quebec, Canada',
  45.5019,
  -73.5674,
  'America/Toronto',
  '2026-05-20',
  '2026-05-22',
  '{"temperature":68.2,"temperature_unit":"F","feels_like":66.9,"humidity":58,"precipitation":0.02,"weather_code":2,"wind_speed":9.1,"observed_at":"2026-05-19T12:00"}',
  '[{"date":"2026-05-20","source":"sample","temperature_max":70.0,"temperature_min":55.0,"precipitation_sum":0.04,"wind_speed_max":13.0,"weather_code":2}]',
  '{"google_maps_url":"https://www.google.com/maps/search/?api=1&query=45.5019,-73.5674","openstreetmap_url":"https://www.openstreetmap.org/?mlat=45.5019&mlon=-73.5674#map=12/45.5019/-73.5674","nearby_display_name":"Montreal, Quebec, Canada","address":{"city":"Montreal","province":"Quebec","country":"Canada"}}',
  'Sample Montreal record'
),
(
  'New York',
  'New York, United States',
  40.7128,
  -74.0060,
  'America/New_York',
  '2026-05-20',
  '2026-05-21',
  '{"temperature":74.5,"temperature_unit":"F","feels_like":73.8,"humidity":52,"precipitation":0.0,"weather_code":1,"wind_speed":10.4,"observed_at":"2026-05-19T12:00"}',
  '[{"date":"2026-05-20","source":"sample","temperature_max":77.0,"temperature_min":63.0,"precipitation_sum":0.0,"wind_speed_max":15.0,"weather_code":1}]',
  '{"google_maps_url":"https://www.google.com/maps/search/?api=1&query=40.7128,-74.006","openstreetmap_url":"https://www.openstreetmap.org/?mlat=40.7128&mlon=-74.006#map=12/40.7128/-74.006","nearby_display_name":"New York, United States","address":{"city":"New York","state":"New York","country":"United States"}}',
  'Sample New York record'
),
(
  'Vancouver',
  'Vancouver, Metro Vancouver Regional District, British Columbia, Canada',
  49.2827,
  -123.1207,
  'America/Vancouver',
  '2026-05-20',
  '2026-05-23',
  '{"temperature":61.7,"temperature_unit":"F","feels_like":60.5,"humidity":64,"precipitation":0.08,"weather_code":3,"wind_speed":7.8,"observed_at":"2026-05-19T12:00"}',
  '[{"date":"2026-05-20","source":"sample","temperature_max":64.0,"temperature_min":52.0,"precipitation_sum":0.12,"wind_speed_max":11.0,"weather_code":3}]',
  '{"google_maps_url":"https://www.google.com/maps/search/?api=1&query=49.2827,-123.1207","openstreetmap_url":"https://www.openstreetmap.org/?mlat=49.2827&mlon=-123.1207#map=12/49.2827/-123.1207","nearby_display_name":"Vancouver, British Columbia, Canada","address":{"city":"Vancouver","province":"British Columbia","country":"Canada"}}',
  'Sample Vancouver record'
);
