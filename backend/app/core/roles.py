from enum import Enum


class UserRole(str, Enum):
    CITIZEN = "citizen"
    MUNICIPALITY = "municipality"
    CONTRACTOR = "contractor"
    FIELD_WORKER = "field_worker"
    ADMIN = "admin"