create or replace view regress.full_multi_level_partitioning as
 SELECT mlp.id,
    mlp.directory_id,
    mlp.ts,
    mlp.is_loaded,
    mlp.duration,
    d.val
   FROM regress.multi_level_partitioning mlp
     JOIN regress.directory d ON d.id = mlp.directory_id;

grant select on table regress.full_multi_level_partitioning to user1;
