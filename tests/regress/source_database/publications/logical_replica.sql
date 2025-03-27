create publication logical_replica;

alter publication logical_replica add table regress.directory;
alter publication logical_replica add table regress.inheritance_partitioning_2024_01;
alter publication logical_replica add table regress.inheritance_partitioning_2024_02;
