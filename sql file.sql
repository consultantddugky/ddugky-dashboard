CREATE TABLE pia (
    prn VARCHAR(100) PRIMARY KEY,
    pia_name VARCHAR(255),
    state VARCHAR(100)
);
select * from pia;
CREATE TABLE sanction_order (
    pia_prn VARCHAR(100),  
    job_role VARCHAR(255),
    total_target INT,
    sc_target INT,
    st_target INT,
    women_target INT,
    pwd_target INT,
    residential_target INT,
    non_residential_target INT,
    FOREIGN KEY (pia_prn) REFERENCES pia(prn)
);
ALTER TABLE sanction_order drop column sanction_order_no;
ALTER TABLE sanction_order add column sanction_order_no varchar(100);
ALTER TABLE sanction_order ADD COLUMN others_target varchar(100);
ALTER TABLE sanction_order ADD COLUMN placements INT;
ALTER TABLE sanction_order MODIFY others_target INT;
ALTER TABLE sanction_order ADD COLUMN r_nr ENUM('Residential', 'Non-Residential');
select * from sanction_order;
CREATE TABLE project_timeline (
    pia_prn VARCHAR(100),
    mou_signing_date DATE,
    pco_date DATE,
    FOREIGN KEY (pia_prn) REFERENCES pia(prn)
);
select * from sanction_order;

CREATE TABLE training_centres (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pia_prn varchar(100),
    centre_name VARCHAR(255),
    district VARCHAR(100),
    state VARCHAR(100),
    male_capacity INT,
    female_capacity INT,
    total_capacity INT,
    r_nr ENUM('Residential', 'Non-Residential'),
    training_centre_capacity INT,
    FOREIGN KEY (pia_prn) REFERENCES pia(prn)
);

CREATE TABLE residential_facility (
    centre_id INT PRIMARY KEY,
    male_capacity INT,
    female_capacity INT,
    total_capacity INT,
    FOREIGN KEY (centre_id) REFERENCES training_centres(id)
);

-- PIA Staff--
CREATE TABLE pia_staff (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pia_prn varchar(100),
    role VARCHAR(100),
    name VARCHAR(255),
    contact VARCHAR(20),
    FOREIGN KEY (pia_prn) REFERENCES pia(prn)
);

CREATE TABLE centre_staff (
    id INT AUTO_INCREMENT PRIMARY KEY,
    centre_id INT,
    role VARCHAR(100),
    name VARCHAR(255),
    contact VARCHAR(20),
    FOREIGN KEY (centre_id) REFERENCES training_centres(id)
);

CREATE TABLE batch (
    batch_code VARCHAR(100) PRIMARY KEY,
    start_date DATE,
    freeze_date DATE,
    ojt_start_date DATE,
    ojt_end_date DATE
);
ALTER TABLE batch ADD COLUMN centre_id INT;
ALTER TABLE batch DROP COLUMN category;
ALTER TABLE batch DROP COLUMN pwd_status;
ALTER TABLE batch DROP COLUMN eligibility;
ALTER TABLE batch DROP COLUMN gender;
ALTER TABLE batch DROP COLUMN address;
ALTER TABLE batch ADD COLUMN total_enrolled int;
ALTER TABLE batch ADD COLUMN candidates_ongoing int;
ALTER TABLE batch ADD COLUMN ojt_ongoing_candidates int;
ALTER TABLE batch ADD COLUMN ojt_completed_candidates int;
ALTER TABLE batch ADD COLUMN pia_prn VARCHAR(100);
ADD FOREIGN KEY (centre_id) REFERENCES training_centres(id);
CREATE TABLE candidates (
	batch_code varchar(100),
    name VARCHAR(255),
    gender VARCHAR(20),
    identity_number VARCHAR(100),
    father_name VARCHAR(255),
    mother_name VARCHAR(255),
	category varchar(100),
    district varchar(100),
    present_address TEXT,
    permanent_address TEXT,
	pwd_status varchar(50),
    contact_details VARCHAR(20),
    alternate_contact VARCHAR(20),
    dob DATE,
    enrollment_date DATE,
    eligibility varchar(100),
    FOREIGN KEY (batch_code) REFERENCES batch(batch_code)
);
ALTER TABLE candidates ADD COLUMN job_role varchar(100);
ALTER TABLE candidates DROP COLUMN candidate_id;
SELECT * FROM candidates;
ALTER TABLE batch MODIFY centre_id INT NOT NULL;
select * from batch;
SELECT 
    b.batch_code, 
    b.start_date, 
    b.freeze_date
FROM batch b
JOIN training_centres tc 
    ON b.centre_id = tc.id
WHERE tc.pia_prn = 'GO2025RF2493';

SELECT b.batch_code, b.centre_id, tc.id, tc.pia_prn
FROM batch b
LEFT JOIN training_centres tc ON b.centre_id = tc.id;

SELECT id, pia_prn FROM training_centres;
UPDATE batch
SET centre_id = 2   
WHERE pia_prn = 'MP2025CR0255';
SELECT b.batch_code, b.centre_id, tc.id, tc.pia_prn
FROM batch b
LEFT JOIN training_centres tc 
ON b.centre_id = tc.id;

ALTER TABLE 
ADD CONSTRAINT fk_centre
FOREIGN KEY (centre_id)
REFERENCES training_centres(id);

select * from sanction_order;
ALTER TABLE batch ADD COLUMN job_role varchar(100);
ALTER TABLE batch ADD COLUMN total_duration int;
ALTER TABLE batch ADD COLUMN ojt_duration int;

SELECT * FROM batch;
UPDATE batch set ojt_duration = '30' where batch_code = 'BT25D100004';
UPDATE batch set total_duration = '720' where batch_code = 'BT25D100004';
ALTER TABLE batch ADD COLUMN male_count int;
ALTER TABLE batch ADD COLUMN female_count int;
DELETE FROM batch 
WHERE batch_code = 'BT26D102774';


ALTER TABLE candidates
DROP FOREIGN KEY candidates_ibfk_1;

ALTER TABLE candidates
ADD CONSTRAINT candidates_ibfk_1
FOREIGN KEY (batch_code)
REFERENCES batch(batch_code)
ON DELETE CASCADE;
select * from batch;
SELECT batch_code, male_count, female_count FROM batch;
UPDATE batch set male_count = '0' where batch_code = 'BT26D101973';
UPDATE batch set female_count = '32' where batch_code = 'BT26D101973';

UPDATE batch set male_count = '11' where batch_code = 'BT26D100175';
UPDATE batch set female_count = '11' where batch_code = 'BT26D100175';

SELECT batch_code, LENGTH(batch_code)
FROM batch
WHERE batch_code LIKE '%BT26D100175%';

UPDATE batch 
SET male_count = 11 
WHERE TRIM(batch_code) = 'BT26D100175';

CREATE TABLE location_data (
    id INT AUTO_INCREMENT PRIMARY KEY,

    pia_prn VARCHAR(50) NOT NULL,
    batch_code VARCHAR(50) NOT NULL,

    state VARCHAR(100) NOT NULL,
    district VARCHAR(100) NOT NULL,
    block_name VARCHAR(100) NOT NULL,

    candidates INT NOT NULL CHECK (candidates > 0),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
select pia_name , prn from pia;
SELECT * FROM location_data;

ALTER TABLE batch ADD COLUMN sc_count int;
ALTER TABLE batch ADD COLUMN st_count int;
ALTER TABLE batch ADD COLUMN others_count int;
select * from batch;
UPDATE batch SET batch_code = 'BT26D100224' where batch_code = 'BT25D100224';
UPDATE batch set sc_count = '2' , st_count = '8' , others_count = '18' where batch_code='BT26D100224';
select * from candidates;
DELETE FROM candidates WHERE batch_code = 'BT25D100004' AND name = 'Aarti Pandurang Kankonkar';
ALTER TABLE candidates DROP COLUMN mother_name;
ALTER TABLE candidates DROP COLUMN alternate_contact;
ALTER TABLE candidates DROP COLUMN permanent_address;
ALTER TABLE candidates DROP COLUMN enrollment_date;
ALTER TABLE candidates ADD COLUMN age int;


LOAD DATA LOCAL INFILE "C:\Users\HP\OneDrive\Documents\candidates.csv"
INTO TABLE candidates
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\r\n'
IGNORE 1 ROWS;

SET GLOBAL local_infile = 1;
SHOW VARIABLES LIKE 'local_infile';

select * from sanction_order;
select * from candidates;
select count(*) from candidates;
DESCRIBE candidates;
DELETE FROM candidates WHERE batch_code = 'BT26D102871';
ALTER TABLE candidates MODIFY contact_details VARCHAR(100);
ALTER TABLE candidates ADD COLUMN village varchar(100);
ALTER TABLE sanction_order ADD COLUMN sector varchar(100);
UPDATE candidates SET eligibility = 'Logistics' where batch_code = 'BT26D101973';

CREATE TABLE village_panchayat_master (
    id INT AUTO_INCREMENT PRIMARY KEY,
    taluka VARCHAR(100) NOT NULL,
    village_panchayat VARCHAR(150) NOT NULL,
    
    UNIQUE KEY unique_village (taluka, village_panchayat)
);

select * from village_panchayat_master;
SELECT 
    v.taluka,
    v.village_panchayat,
    COUNT(c.id) AS candidate_count
FROM village_panchayat_master v
LEFT JOIN candidates c 
    ON v.village_panchayat = c.village
GROUP BY v.taluka, v.village_panchayat
ORDER BY v.taluka, v.village_panchayat;


SELECT 
    v.taluka,
    v.village_panchayat,
    COUNT(c.village) AS candidate_count
FROM village_panchayat_master v
LEFT JOIN candidates c 
    ON LOWER(TRIM(v.village_panchayat)) = LOWER(TRIM(c.village))
GROUP BY v.taluka, v.village_panchayat
ORDER BY v.taluka, v.village_panchayat;

SELECT 
    v.taluka,
    COUNT(*) 
FROM candidates c
LEFT JOIN village_panchayat_master v
ON LOWER(TRIM(v.village_panchayat)) = LOWER(TRIM(c.village))
WHERE v.taluka LIKE '%tis%'
GROUP BY v.taluka;


