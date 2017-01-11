db.createUser(
{
   user: "admin",
   pwd:  "mdcs4odi",
   roles: [ { role: "userAdminAnyDatabase", db: "admin"},"backup","restore"]
}
);
