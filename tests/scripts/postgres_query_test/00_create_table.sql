CREATE TABLE test_table (
    equip_id serial PRIMARY KEY,
    type varchar (50) NOT NULL,
    color varchar (25) NOT NULL,
    location varchar(25) check (location in ('north', 'south', 'west', 'east', 'northeast', 'southeast', 'southwest', 'northwest')),
    install_date date
);

INSERT INTO test_table (type, color, location, install_date) VALUES ('slide', 'blue', 'south', '2014-04-28');
