CREATE TABLE app_settings (
	"key" VARCHAR NOT NULL, 
	value VARCHAR NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY ("key")
);
CREATE TABLE automation_messages (
	id VARCHAR NOT NULL, 
	automation_id VARCHAR NOT NULL, 
	position INTEGER NOT NULL, 
	text VARCHAR NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(automation_id) REFERENCES automations (id)
);
CREATE TABLE automation_schedules (
	id VARCHAR NOT NULL, 
	automation_id VARCHAR NOT NULL, 
	message_id VARCHAR NOT NULL, 
	schedule_id VARCHAR NOT NULL, 
	recipient_chat_id VARCHAR NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(automation_id) REFERENCES automations (id), 
	FOREIGN KEY(message_id) REFERENCES automation_messages (id), 
	FOREIGN KEY(schedule_id) REFERENCES schedules (id)
);
CREATE TABLE automations (
	id VARCHAR NOT NULL, 
	event_id VARCHAR NOT NULL, 
	offset_amount INTEGER NOT NULL, 
	offset_unit VARCHAR(7) NOT NULL, 
	offset_direction VARCHAR(6) NOT NULL, 
	custom_time_local VARCHAR, 
	custom_interval VARCHAR, 
	message_gap_seconds INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(event_id) REFERENCES events (id)
);
CREATE TABLE billing_profiles (
	id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	legal_name VARCHAR NOT NULL, 
	postal_code VARCHAR NOT NULL, 
	address VARCHAR NOT NULL, 
	number VARCHAR NOT NULL, 
	complement VARCHAR NOT NULL, 
	neighborhood VARCHAR NOT NULL, 
	city VARCHAR NOT NULL, 
	state VARCHAR NOT NULL, 
	country VARCHAR NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE TABLE cached_messages (
	message_id VARCHAR NOT NULL, 
	user_id VARCHAR, 
	chat_id VARCHAR NOT NULL, 
	ts INTEGER NOT NULL, 
	from_me BOOLEAN NOT NULL, 
	body VARCHAR NOT NULL, 
	msg_type VARCHAR NOT NULL, 
	has_media BOOLEAN NOT NULL, 
	ack_name VARCHAR, 
	synced_at DATETIME NOT NULL, 
	PRIMARY KEY (message_id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE TABLE calendar_connections (
	id VARCHAR NOT NULL, 
	user_id VARCHAR, 
	provider VARCHAR NOT NULL, 
	account_identifier VARCHAR NOT NULL, 
	access_token_enc VARCHAR NOT NULL, 
	refresh_token_enc VARCHAR NOT NULL, 
	token_expires_at DATETIME NOT NULL, 
	scope VARCHAR NOT NULL, 
	status VARCHAR(12) NOT NULL, 
	last_sync_at DATETIME, 
	last_sync_error VARCHAR, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE TABLE calendars (
	id VARCHAR NOT NULL, 
	connection_id VARCHAR NOT NULL, 
	external_id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	time_zone VARCHAR NOT NULL, 
	color VARCHAR, 
	enabled BOOLEAN NOT NULL, 
	sync_token VARCHAR, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_calendar_connection_external UNIQUE (connection_id, external_id), 
	FOREIGN KEY(connection_id) REFERENCES calendar_connections (id)
);
CREATE TABLE dispatches (
	id VARCHAR NOT NULL, 
	schedule_id VARCHAR NOT NULL, 
	scheduled_at_utc DATETIME NOT NULL, 
	status VARCHAR(10) NOT NULL, 
	attempts INTEGER NOT NULL, 
	last_error VARCHAR, 
	waha_message_id VARCHAR, 
	sent_at_utc DATETIME, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(schedule_id) REFERENCES schedules (id)
);
CREATE TABLE email_verification_tokens (
	id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	token_hash VARCHAR NOT NULL, 
	created_at DATETIME NOT NULL, 
	expires_at DATETIME NOT NULL, 
	used_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE TABLE event_automations (
	id VARCHAR NOT NULL, 
	event_id VARCHAR NOT NULL, 
	schedule_id VARCHAR NOT NULL, 
	offset_amount INTEGER NOT NULL, 
	offset_unit VARCHAR(7) NOT NULL, 
	offset_direction VARCHAR(6) NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(event_id) REFERENCES events (id), 
	FOREIGN KEY(schedule_id) REFERENCES schedules (id)
);
CREATE TABLE event_sync_status (
	event_id VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	error VARCHAR, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (event_id), 
	FOREIGN KEY(event_id) REFERENCES events (id)
);
CREATE TABLE events (
	id VARCHAR NOT NULL, 
	user_id VARCHAR, 
	source VARCHAR(8) NOT NULL, 
	calendar_id VARCHAR, 
	external_id VARCHAR, 
	recurring_event_id VARCHAR, 
	title VARCHAR NOT NULL, 
	description VARCHAR NOT NULL, 
	start_utc DATETIME NOT NULL, 
	end_utc DATETIME NOT NULL, 
	timezone VARCHAR NOT NULL, 
	all_day BOOLEAN NOT NULL, 
	status VARCHAR(9) NOT NULL, 
	provider_updated_at DATETIME, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_event_calendar_external UNIQUE (calendar_id, external_id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(calendar_id) REFERENCES calendars (id)
);
CREATE TABLE login_audit_events (
	id VARCHAR NOT NULL, 
	user_id VARCHAR, 
	event_type VARCHAR(24) NOT NULL, 
	detail VARCHAR, 
	ip_address VARCHAR, 
	user_agent VARCHAR, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE TABLE password_reset_tokens (
	id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	token_hash VARCHAR NOT NULL, 
	created_at DATETIME NOT NULL, 
	expires_at DATETIME NOT NULL, 
	used_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE TABLE schedule_dependencies (
	schedule_id VARCHAR NOT NULL, 
	depends_on_schedule_id VARCHAR NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (schedule_id), 
	FOREIGN KEY(schedule_id) REFERENCES schedules (id), 
	FOREIGN KEY(depends_on_schedule_id) REFERENCES schedules (id)
);
CREATE TABLE schedule_groups (
	id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	source VARCHAR(12) NOT NULL, 
	session VARCHAR NOT NULL, 
	recipient_input VARCHAR NOT NULL, 
	recipient_name VARCHAR, 
	chat_id VARCHAR NOT NULL, 
	timezone VARCHAR NOT NULL, 
	start_local DATETIME NOT NULL, 
	message_gap_seconds INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE TABLE schedules (
	id VARCHAR NOT NULL, 
	user_id VARCHAR, 
	group_id VARCHAR, 
	position INTEGER NOT NULL, 
	session VARCHAR NOT NULL, 
	recipient_input VARCHAR NOT NULL, 
	chat_id VARCHAR NOT NULL, 
	text VARCHAR NOT NULL, 
	timezone VARCHAR NOT NULL, 
	first_run_local DATETIME NOT NULL, 
	recurrence VARCHAR, 
	enabled BOOLEAN NOT NULL, 
	max_attempts INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(group_id) REFERENCES schedule_groups (id)
);
CREATE TABLE user_sessions (
	id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	token_hash VARCHAR NOT NULL, 
	created_at DATETIME NOT NULL, 
	last_seen_at DATETIME NOT NULL, 
	expires_at DATETIME NOT NULL, 
	user_agent VARCHAR, 
	ip_address VARCHAR, 
	revoked_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE TABLE users (
	id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	email VARCHAR NOT NULL, 
	password_hash VARCHAR NOT NULL, 
	phone VARCHAR, 
	waha_session VARCHAR NOT NULL, 
	timezone VARCHAR, 
	email_verified BOOLEAN NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	onboarding_completed_at DATETIME, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_user_email UNIQUE (email)
);
CREATE TABLE whatsapp_sessions (
	id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	session_name VARCHAR NOT NULL, 
	engine VARCHAR, 
	disconnected_at DATETIME, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX ix_automation_messages_automation_id ON automation_messages (automation_id);
CREATE INDEX ix_automation_schedules_automation_id ON automation_schedules (automation_id);
CREATE INDEX ix_automation_schedules_message_id ON automation_schedules (message_id);
CREATE INDEX ix_automation_schedules_recipient_chat_id ON automation_schedules (recipient_chat_id);
CREATE UNIQUE INDEX ix_automation_schedules_schedule_id ON automation_schedules (schedule_id);
CREATE INDEX ix_automations_event_id ON automations (event_id);
CREATE UNIQUE INDEX ix_billing_profiles_user_id ON billing_profiles (user_id);
CREATE INDEX ix_cached_messages_chat_id ON cached_messages (chat_id);
CREATE INDEX ix_cached_messages_ts ON cached_messages (ts);
CREATE INDEX ix_cached_messages_user_id ON cached_messages (user_id);
CREATE INDEX ix_calendar_connections_provider ON calendar_connections (provider);
CREATE INDEX ix_calendar_connections_status ON calendar_connections (status);
CREATE INDEX ix_calendar_connections_user_id ON calendar_connections (user_id);
CREATE INDEX ix_calendars_connection_id ON calendars (connection_id);
CREATE INDEX ix_calendars_enabled ON calendars (enabled);
CREATE INDEX ix_dispatches_schedule_id ON dispatches (schedule_id);
CREATE INDEX ix_dispatches_schedule_status ON dispatches (schedule_id, status);
CREATE INDEX ix_dispatches_scheduled_at_utc ON dispatches (scheduled_at_utc);
CREATE INDEX ix_dispatches_status ON dispatches (status);
CREATE INDEX ix_dispatches_status_scheduled ON dispatches (status, scheduled_at_utc);
CREATE UNIQUE INDEX ix_email_verification_tokens_token_hash ON email_verification_tokens (token_hash);
CREATE INDEX ix_email_verification_tokens_user_id ON email_verification_tokens (user_id);
CREATE INDEX ix_event_automations_event_id ON event_automations (event_id);
CREATE UNIQUE INDEX ix_event_automations_schedule_id ON event_automations (schedule_id);
CREATE INDEX ix_events_calendar_id ON events (calendar_id);
CREATE INDEX ix_events_source ON events (source);
CREATE INDEX ix_events_start_utc ON events (start_utc);
CREATE INDEX ix_events_status ON events (status);
CREATE INDEX ix_events_user_id ON events (user_id);
CREATE INDEX ix_events_user_start ON events (user_id, start_utc);
CREATE INDEX ix_login_audit_events_created_at ON login_audit_events (created_at);
CREATE INDEX ix_login_audit_events_event_type ON login_audit_events (event_type);
CREATE INDEX ix_login_audit_events_user_id ON login_audit_events (user_id);
CREATE UNIQUE INDEX ix_password_reset_tokens_token_hash ON password_reset_tokens (token_hash);
CREATE INDEX ix_password_reset_tokens_user_id ON password_reset_tokens (user_id);
CREATE INDEX ix_schedule_dependencies_depends_on_schedule_id ON schedule_dependencies (depends_on_schedule_id);
CREATE INDEX ix_schedule_groups_chat_id ON schedule_groups (chat_id);
CREATE INDEX ix_schedule_groups_source ON schedule_groups (source);
CREATE INDEX ix_schedule_groups_user_id ON schedule_groups (user_id);
CREATE INDEX ix_schedules_chat_id ON schedules (chat_id);
CREATE INDEX ix_schedules_enabled ON schedules (enabled);
CREATE INDEX ix_schedules_group_id ON schedules (group_id);
CREATE INDEX ix_schedules_user_chat ON schedules (user_id, session, chat_id);
CREATE INDEX ix_schedules_user_id ON schedules (user_id);
CREATE UNIQUE INDEX ix_user_sessions_token_hash ON user_sessions (token_hash);
CREATE INDEX ix_user_sessions_user_id ON user_sessions (user_id);
CREATE INDEX ix_users_email ON users (email);
CREATE UNIQUE INDEX ix_users_waha_session ON users (waha_session);
CREATE UNIQUE INDEX ix_whatsapp_sessions_session_name ON whatsapp_sessions (session_name);
CREATE INDEX ix_whatsapp_sessions_user_id ON whatsapp_sessions (user_id);
