from extensions import db
from sqlalchemy.sql import func, text

class Roles(db.Model):
    __tablename__ = 'roles'
    role_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    role_name = db.Column(db.Text)
    time_stamp = db.Column(db.BigInteger)

    def to_dict(self):
        return {
            'role_id': self.role_id,
            'role_name': self.role_name,
            'time_stamp': self.time_stamp
        }

class ContentAccessGroups(db.Model):
    __tablename__ = 'content_access_groups'
    access_group_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    group_name = db.Column(db.Text)
    time_stamp = db.Column(db.BigInteger)

    def to_dict(self):
        return {
            'access_group_id': self.access_group_id,
            'group_name': self.group_name,
            'time_stamp': self.time_stamp
        }
            
class Users(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Text, primary_key=True)
    password = db.Column(db.Text)
    company = db.Column(db.Text)
    department = db.Column(db.Text)
    position = db.Column(db.Text)
    name = db.Column(db.Text)
    access_group_id = db.Column(db.Integer, db.ForeignKey('content_access_groups.access_group_id'))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.role_id'))
    time_stamp = db.Column(db.BigInteger)
    logout_time = db.Column(db.DateTime(timezone=True))
    login_time = db.Column(db.DateTime(timezone=True))
    is_deleted = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'password': self.password,
            'company': self.company,
            'department': self.department,
            'position': self.position,
            'name': self.name,
            'access_group_id': self.access_group_id,
            'role_id': self.role_id,
            'time_stamp': self.time_stamp,
            'logout_time': self.logout_time,
            'login_time': self.login_time,
            'is_deleted': self.is_deleted
        }

class LoginHistory(db.Model):
    __tablename__ = 'login_history'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Text, db.ForeignKey('users.id'))
    ip_address = db.Column(db.Text)
    login_time = db.Column(db.DateTime(timezone=True))
    logout_time = db.Column(db.DateTime(timezone=True))
    session_duration = db.Column(db.Interval)
    time_stamp = db.Column(db.BigInteger)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'ip_address': self.ip_address,
            'login_time': self.login_time,
            'logout_time': self.logout_time,
            'session_duration': self.session_duration,
            'time_stamp': self.time_stamp
        }

class loginSummaryDay(db.Model):
    __tablename__ = 'login_summary_day'
    period_value = db.Column(db.Date)
    scope = db.Column(db.Text)
    company_id = db.Column(db.Integer)
    company = db.Column(db.Text)
    department = db.Column(db.Text)
    user_id = db.Column(db.Text)
    user_name = db.Column(db.Text)
    total_duration = db.Column(db.Interval)
    worktime_duration = db.Column(db.Interval)
    offhour_duration = db.Column(db.Interval)
    internal_count = db.Column(db.Integer)
    external_count = db.Column(db.Integer)
    company_key = db.Column(db.Text)
    department_key = db.Column(db.Text)
    user_id_key = db.Column(db.Text)
    
    __table_args__ = (
        db.PrimaryKeyConstraint('period_value', 'scope', 'company_key', 'department_key', 'user_id_key',
                                name='login_summary_day_pkey'
                                ),
    )
    
    def to_dict(self):
        return {
            'period_value': self.period_value,
            'scope': self.scope,
            'company_id': self.company_id,
            'company': self.company,
            'department': self.department,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'total_duration': str(self.total_duration),
            'worktime_duration': str(self.worktime_duration),
            'offhour_duration': str(self.offhour_duration),
            'internal_count': self.internal_count,
            'external_count': self.external_count,
            'company_key': self.company_key,
            'department_key': self.department_key,
            'user_id_key': self.user_id_key
        }
        
class loginSummaryAgg(db.Model):
    __tablename__ = 'login_summary_agg'
    period_type = db.Column(db.Text)
    period_value = db.Column(db.Text)
    scope = db.Column(db.Text)
    company_id = db.Column(db.Integer)
    company = db.Column(db.Text)
    department = db.Column(db.Text)
    user_id = db.Column(db.Text)
    user_name = db.Column(db.Text)
    total_duration = db.Column(db.Interval)
    worktime_duration = db.Column(db.Interval)
    offhour_duration = db.Column(db.Interval)
    internal_count = db.Column(db.Integer)
    external_count = db.Column(db.Integer)
    company_key = db.Column(db.Text)
    department_key = db.Column(db.Text)
    user_id_key = db.Column(db.Text)
    
    __table_args__ = (
        db.PrimaryKeyConstraint('period_type', 'period_value', 'scope', 'company_key', 'department_key', 'user_id_key',
                                name='login_summary_agg_pkey'
                                ),
    )
    
    def to_dict(self):
        return {
            'period_type': self.period_type,
            'period_value': self.period_value,
            'scope': self.scope,
            'company_id': self.company_id,
            'company': self.company,
            'department': self.department,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'total_duration': self.total_duration,
            'worktime_duration': self.worktime_duration,
            'offhour_duration': self.offhour_duration,
            'internal_count': self.internal_count,
            'external_count': self.external_count,
            'company_key': self.company_key,
            'department_key': self.department_key,
            'user_id_key': self.user_id_key
        }
    
         
class ContentViewingHistory(db.Model):
    __tablename__ = 'content_viewing_history'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Text, db.ForeignKey('users.id'))
    file_id = db.Column(db.Text, db.ForeignKey('files.file_id'))
    start_time = db.Column(db.DateTime(timezone=True))
    end_time = db.Column(db.DateTime(timezone=True))
    stay_duration = db.Column(db.Interval)
    ip_address = db.Column(db.Text)
    time_stamp = db.Column(db.BigInteger)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'file_id': self.file_id,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'stay_duration': self.stay_duration,
            'ip_address': self.ip_address,
            'time_stamp': self.time_stamp
        }
        
        
class Folders(db.Model):
    __tablename__ = 'folders'
    folder_id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('folders.folder_id'))
    folder_name = db.Column(db.Text)
    depth = db.Column(db.SmallInteger)
    is_visible = db.Column(db.Boolean)
    folder_type = db.Column(db.String(20))
    create_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    update_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    time_stamp = db.Column(db.BigInteger)
    is_deleted = db.Column(db.Boolean, default=False)
    top_category_folder_id = db.Column(db.Integer)

    def to_dict(self):
        return {
            'folder_id': self.folder_id,
            'parent_id': self.parent_id,
            'folder_name': self.folder_name,
            'depth': self.depth,
            'is_visible': self.is_visible,
            'folder_type': self.folder_type,
            'create_at': self.create_at,
            'update_at': self.update_at,
            'time_stamp': self.time_stamp,
            'is_deleted': self.is_deleted,
            'top_category_folder_id': self.top_category_folder_id        
        }
        
class Files(db.Model):
    __tablename__ = 'files'
    file_id = db.Column(db.Integer, primary_key=True)
    folder_id = db.Column(db.Integer, db.ForeignKey('folders.folder_id'))
    file_name = db.Column(db.Text)
    file_type = db.Column(db.String(10))
    file_size = db.Column(db.BigInteger)
    file_path = db.Column(db.Text)
    create_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    update_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    time_stamp = db.Column(db.BigInteger)
    is_deleted = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'file_id': self.file_id,
            'folder_id': self.folder_id,
            'file_name': self.file_name,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'file_path': self.file_path,
            'create_at': self.create_at,
            'update_at': self.update_at,
            'time_stamp': self.time_stamp,
            'is_deleted': self.is_deleted
       
        }

class MemoData(db.Model):
    __tablename__ = 'memos'
    
    id = db.Column(db.String, primary_key=True)
    serial_number = db.Column(db.Integer, nullable=False)
    modified_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    user_id = db.Column(db.String, nullable=True)
    content = db.Column(db.String, nullable=True)
    path = db.Column(db.String, nullable=True)
    rel_position_x = db.Column(db.Float, nullable=False)  # double in C#
    rel_position_y = db.Column(db.Float, nullable=False)  # double in C#
    world_position_x = db.Column(db.Float, nullable=False)  # double in C#
    world_position_y = db.Column(db.Float, nullable=False)  # double in C#
    world_position_z = db.Column(db.Float, nullable=False)  # double in C#
    status = db.Column(db.Integer, nullable=False)  # uint in C#
    time_stamp = db.Column(db.BigInteger, nullable=True)  # Added for DB tracking

    def to_dict(self):
        return {
            'id': self.id,
            'serial_number': self.serial_number,
            'modified_at': self.modified_at,
            'user_id': self.user_id,
            'content': self.content,
            'path': self.path,
            'relPositionX': self.rel_position_x,  # Match C# JsonPropertyName
            'relPositionY': self.rel_position_y,  # Match C# JsonPropertyName
            'worldPositionX': self.world_position_x,  # Match C# JsonPropertyName
            'worldPositionY': self.world_position_y,  # Match C# JsonPropertyName
            'worldPositionZ': self.world_position_z,  # Match C# JsonPropertyName
            'status': self.status,  # Match C# JsonPropertyName
            'time_stamp': self.time_stamp
        }