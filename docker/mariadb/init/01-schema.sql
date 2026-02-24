-- ===========================
-- KG_db 스키마 정의 (2026-02-24)
-- ===========================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table: users
-- ----------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
	`user_id` BIGINT NOT NULL AUTO_INCREMENT,
	`login_id` VARCHAR(50) NOT NULL COMMENT '로그인 아이디',
	`password_hash` VARCHAR(255) NOT NULL,
	`name` VARCHAR(50) NOT NULL,
	`role` VARCHAR(50) NULL,
	`subject` VARCHAR(50) NOT NULL,
	`memo` VARCHAR(50) NULL,
	`created_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
	`updated_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	`is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '계정 활성화 여부',
	`email` VARCHAR(50) NULL COMMENT '이메일',
	`team_name` VARCHAR(100) NULL,
	PRIMARY KEY (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: user_preferences
-- ----------------------------
DROP TABLE IF EXISTS `user_preferences`;
CREATE TABLE `user_preferences` (
	`pref_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT 'pk',
	`user_id` BIGINT NOT NULL,
	`blocklist_json` LONGTEXT NULL COMMENT '부정어 리스트',
	PRIMARY KEY (`pref_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: achievement
-- ----------------------------
DROP TABLE IF EXISTS `achievement`;
CREATE TABLE `achievement` (
	`ach_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '성취기준 id',
	`code` VARCHAR(50) NULL COMMENT '성취기준 코드 (예: 9국01-01)',
	`description` TEXT NULL COMMENT '성취기준 내용',
	`evaluation_criteria` TEXT NULL COMMENT '평가기준',
	PRIMARY KEY (`ach_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: project_scopes
-- ----------------------------
DROP TABLE IF EXISTS `project_scopes`;
CREATE TABLE `project_scopes` (
	`scope_id` BIGINT NOT NULL AUTO_INCREMENT,
	`large_unit_id` INT NULL COMMENT '대단원 ID (API)',
	`large_unit_name` VARCHAR(100) NULL,
	`small_unit_id` INT NULL COMMENT '소단원 ID (API)',
	`small_unit_name` VARCHAR(100) NULL,
	`publisher_author` VARCHAR(50) NULL COMMENT '출판사 및 저자',
	`grade` INT NULL,
	`semester` TINYINT NULL,
	`subject` VARCHAR(50) NULL COMMENT '교과목',
	`learning_objective` TEXT NULL COMMENT '학습목표',
	`learning_activity` TEXT NULL COMMENT '학습활동',
	`learning_element` TEXT NULL COMMENT '학습요소',
	`achievement_ids` LONGTEXT NULL COMMENT '성취기준 맵핑 [1, 5, 12]',
	`study_area` VARCHAR(50) NULL COMMENT '영역(예: 말하기듣기, 매체 등)',
	`school_level` VARCHAR(50) NULL DEFAULT '중학교' COMMENT '학교급(예: 중학교, 고등학교)',
	PRIMARY KEY (`scope_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: projects
-- ----------------------------
DROP TABLE IF EXISTS `projects`;
CREATE TABLE `projects` (
	`project_id` BIGINT NOT NULL AUTO_INCREMENT,
	`user_id` BIGINT NOT NULL,
	`scope_id` BIGINT NULL,
	`project_name` VARCHAR(100) NOT NULL,
	`status` ENUM('WRITING', 'GENERATING', 'COMPLETED', 'FAILED') NULL DEFAULT 'WRITING' COMMENT '작성중/생성중/완료/실패',
	`is_deleted` TINYINT(1) NULL DEFAULT 0 COMMENT '삭제 여부',
	`created_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
	`updated_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	PRIMARY KEY (`project_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: passages
-- ----------------------------
DROP TABLE IF EXISTS `passages`;
CREATE TABLE `passages` (
	`passage_id` BIGINT NOT NULL AUTO_INCREMENT,
	`title` VARCHAR(100) NULL,
	`context` LONGTEXT NOT NULL,
	`auth` VARCHAR(50) NULL,
	`scope_id` BIGINT NULL,
	PRIMARY KEY (`passage_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: passage_custom
-- ----------------------------
DROP TABLE IF EXISTS `passage_custom`;
CREATE TABLE `passage_custom` (
	`custom_passage_id` BIGINT NOT NULL AUTO_INCREMENT,
	`user_id` BIGINT NOT NULL,
	`scope_id` BIGINT NULL,
	`custom_title` VARCHAR(100) NULL,
	`title` VARCHAR(50) NULL,
	`auth` VARCHAR(50) NULL,
	`context` LONGTEXT NOT NULL,
	`passage_id` BIGINT NULL COMMENT '원본 지문이 있는 경우',
	`created_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
	`is_use` INT NULL DEFAULT 1 COMMENT '지문 사용 여부',
	PRIMARY KEY (`custom_passage_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: project_source_config
-- ----------------------------
DROP TABLE IF EXISTS `project_source_config`;
CREATE TABLE `project_source_config` (
	`config_id` BIGINT NOT NULL AUTO_INCREMENT,
	`project_id` BIGINT NULL,
	`is_modified` TINYINT(1) NULL COMMENT '지문 변형 여부 0: 원본사용, 1: 수정본 사용, 2: 지문없이 사용, 4: 지문 수정 중',
	`passage_id` BIGINT NULL COMMENT '원본소스를 사용했다면 기록',
	`custom_passage_id` BIGINT NULL COMMENT '업로드한 지문 아이디',
	`question_type` VARCHAR(50) NULL COMMENT '문항유형 (예: 5지선다, 단답형, 진위형, 선긋기)',
	`target_count` INT NULL COMMENT '요청한 문항 수',
	`pref_id` BIGINT NULL COMMENT '부정어 리스트 아이디',
	`additional_prompt` TEXT NULL COMMENT '추가 프롬프트',
	`use_ai_model` TINYINT(1) NULL COMMENT 'AI 생성 요청 여부',
	`stem_directive` TEXT NULL COMMENT '발문 지시문 (예: ~로 알맞은 것은?)',
	`created_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
	`updated_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
	`input_tokens` INT NULL COMMENT '사용한 총 입력 토큰',
	`output_tokens` INT NULL COMMENT '사용한 총 출력 토큰',
	`model_name` VARCHAR(50) NULL COMMENT 'LLM 모델명',
	`use_passage` TINYINT(1) NULL,
	PRIMARY KEY (`config_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: batch_logs
-- ----------------------------
DROP TABLE IF EXISTS `batch_logs`;
CREATE TABLE `batch_logs` (
	`batch_id` BIGINT NOT NULL AUTO_INCREMENT,
	`input_token` INT NULL,
	`output_token` INT NULL,
	`total_duration` INT NULL,
	`temperature` FLOAT NULL,
	`top_p` FLOAT NULL,
	`top_k` FLOAT NULL,
	`model_name` VARCHAR(50) NULL COMMENT 'LLM 모델명',
	`total_attempts` INT NULL COMMENT '한번에 요청한 문항 수',
	`success_count` INT NULL COMMENT '생성 성공한 문항 수',
	`error_message` TEXT NULL COMMENT '에러 발생 시 기록용',
	`created_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (`batch_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: multiple_choice_questions
-- ----------------------------
DROP TABLE IF EXISTS `multiple_choice_questions`;
CREATE TABLE `multiple_choice_questions` (
	`question_id` BIGINT NOT NULL AUTO_INCREMENT,
	`config_id` BIGINT NULL COMMENT '생성설정 아이디',
	`batch_id` BIGINT NOT NULL COMMENT '배치 로그 아이디',
	`project_id` BIGINT NOT NULL COMMENT '프로젝트 아이디',
	`question` LONGTEXT NULL COMMENT '문제 발문',
	`box_content` LONGTEXT NULL COMMENT '보기 박스에 들어갈 내용',
	`option1` LONGTEXT NULL COMMENT '객관식 답안1',
	`option2` LONGTEXT NULL COMMENT '객관식 답안2',
	`option3` LONGTEXT NULL COMMENT '객관식 답안3',
	`option4` LONGTEXT NULL COMMENT '객관식 답안4',
	`option5` LONGTEXT NULL COMMENT '객관식 답안5',
	`answer` VARCHAR(50) NULL COMMENT '정답 답안 번호 (여러개일 경우 ,로 구분)',
	`answer_explain` LONGTEXT NULL,
	`feedback_score` DECIMAL(3, 1) NULL COMMENT '0.5~10점 평가',
	`is_used` TINYINT(1) NULL COMMENT '문항 사용여부',
	`llm_difficulty` VARCHAR(50) NULL COMMENT 'LLM이 설정한 난이도',
	`modified_difficulty` VARCHAR(50) NULL COMMENT '사용자 수정 난이도',
	`created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	`updated_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	`modified_passage` LONGTEXT NULL COMMENT '변형된 지문',
	`is_checked` TINYINT NULL DEFAULT 1 COMMENT '다운로드 사용 유무',
	PRIMARY KEY (`question_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: short_answer_questions
-- ----------------------------
DROP TABLE IF EXISTS `short_answer_questions`;
CREATE TABLE `short_answer_questions` (
	`short_question_id` BIGINT NOT NULL AUTO_INCREMENT,
	`config_id` BIGINT NULL,
	`batch_id` BIGINT NOT NULL,
	`project_id` BIGINT NOT NULL COMMENT '프로젝트 아이디',
	`question` LONGTEXT NULL COMMENT '문제 발문',
	`answer` VARCHAR(255) NULL COMMENT '정답 (여러개일 경우 ,로 구분)',
	`answer_explain` LONGTEXT NULL,
	`is_used` TINYINT(1) NULL,
	`box_content` LONGTEXT NULL COMMENT '보기 박스에 들어갈 내용',
	`feedback_score` DECIMAL(3, 1) NULL COMMENT '0.5~10점 평가',
	`created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	`updated_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	`is_checked` TINYINT NULL DEFAULT 1 COMMENT '다운로드 체크',
	`modified_passage` LONGTEXT NULL COMMENT '변형된 지문',
	`llm_difficulty` VARCHAR(50) NULL,
	`modified_difficulty` VARCHAR(50) NULL COMMENT '변경된 난이도',
	PRIMARY KEY (`short_question_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: true_false_questions
-- ----------------------------
DROP TABLE IF EXISTS `true_false_questions`;
CREATE TABLE `true_false_questions` (
	`ox_question_id` BIGINT NOT NULL AUTO_INCREMENT,
	`config_id` BIGINT NULL,
	`batch_id` BIGINT NOT NULL,
	`project_id` BIGINT NOT NULL COMMENT '프로젝트 아이디',
	`feedback_score` DECIMAL(3, 1) NULL COMMENT '0.5~10점 평가',
	`question` LONGTEXT NULL COMMENT '문제 발문',
	`answer` VARCHAR(50) NULL COMMENT 'O 또는 X',
	`answer_explain` LONGTEXT NULL,
	`is_used` TINYINT(1) NULL COMMENT '문항사용여부',
	`created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	`updated_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	`is_checked` TINYINT NULL DEFAULT 1 COMMENT '다운로드 여부',
	`modified_passage` LONGTEXT NULL,
	`llm_difficulty` VARCHAR(50) NULL,
	`modified_difficulty` VARCHAR(50) NULL,
	`box_content` LONGTEXT NULL,
	PRIMARY KEY (`ox_question_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: matching_questions
-- ----------------------------
DROP TABLE IF EXISTS `matching_questions`;
CREATE TABLE `matching_questions` (
	`matching_question_id` BIGINT NOT NULL AUTO_INCREMENT,
	`config_id` BIGINT NULL,
	`batch_id` BIGINT NOT NULL,
	`project_id` BIGINT NOT NULL COMMENT '프로젝트 아이디',
	`question` LONGTEXT NULL COMMENT '문제 발문',
	`answer_explain` LONGTEXT NULL,
	`is_used` TINYINT(1) NULL COMMENT '문항사용여부',
	`box_content` LONGTEXT NULL COMMENT '보기 박스에 들어갈 내용',
	`feedback_score` DECIMAL(3, 1) NULL COMMENT '0.5~10점 평가',
	`created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	`updated_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	`is_checked` TINYINT NULL DEFAULT 1 COMMENT '다운로드 체크',
	`modified_passage` LONGTEXT NULL COMMENT '변형된 지문',
	`llm_difficulty` VARCHAR(50) NULL,
	`modified_difficulty` VARCHAR(50) NULL COMMENT '변경된 난이도',
	`left_items` LONGTEXT NULL COMMENT '왼쪽 보기 배열 (JSON)',
	`right_items` LONGTEXT NULL COMMENT '오른쪽 보기 배열 (JSON)',
	`sort_order` LONGTEXT NULL COMMENT '표시 순서 (JSON)',
	PRIMARY KEY (`matching_question_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: log_selection
-- ----------------------------
DROP TABLE IF EXISTS `log_selection`;
CREATE TABLE `log_selection` (
	`selection_id` BIGINT NOT NULL AUTO_INCREMENT,
	`project_id` BIGINT NULL,
	`selected_list` LONGTEXT NULL COMMENT '선택한 문항 리스트',
	`created_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (`selection_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: log_download
-- ----------------------------
DROP TABLE IF EXISTS `log_download`;
CREATE TABLE `log_download` (
	`download_id` BIGINT NOT NULL AUTO_INCREMENT,
	`selection_id` BIGINT NULL,
	`download_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (`download_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: generation_logs
-- ----------------------------
DROP TABLE IF EXISTS `generation_logs`;
CREATE TABLE `generation_logs` (
	`generation_log_id` BIGINT NOT NULL AUTO_INCREMENT,
	`config_id` BIGINT NULL COMMENT '생성 설정 아이디',
	`project_id` BIGINT NOT NULL COMMENT '프로젝트 고유값',
	`question_type` VARCHAR(50) NULL COMMENT '문항타입',
	`input_token` INT NULL COMMENT '사용한 총 인풋토큰',
	`output_token` INT NULL COMMENT '사용한 총 출력토큰',
	`model_name` VARCHAR(50) NULL,
	PRIMARY KEY (`generation_log_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ===========================
-- FK 제약조건
-- ===========================

-- users 참조
ALTER TABLE `user_preferences`
ADD CONSTRAINT `FK_users_TO_user_preferences` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`);
ALTER TABLE `projects`
ADD CONSTRAINT `FK_users_TO_projects` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`);
ALTER TABLE `passage_custom`
ADD CONSTRAINT `FK_users_TO_passage_custom` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`);

-- project_scopes 참조
ALTER TABLE `projects`
ADD CONSTRAINT `FK_project_scopes_TO_projects` FOREIGN KEY (`scope_id`) REFERENCES `project_scopes` (`scope_id`);
ALTER TABLE `passages`
ADD CONSTRAINT `FK_project_scopes_TO_passages` FOREIGN KEY (`scope_id`) REFERENCES `project_scopes` (`scope_id`);
ALTER TABLE `passage_custom`
ADD CONSTRAINT `FK_project_scopes_TO_passage_custom` FOREIGN KEY (`scope_id`) REFERENCES `project_scopes` (`scope_id`);

-- projects 참조
ALTER TABLE `project_source_config`
ADD CONSTRAINT `FK_projects_TO_project_source_config` FOREIGN KEY (`project_id`) REFERENCES `projects` (`project_id`);
ALTER TABLE `multiple_choice_questions`
ADD CONSTRAINT `FK_projects_TO_multiple_choice_questions` FOREIGN KEY (`project_id`) REFERENCES `projects` (`project_id`);
ALTER TABLE `short_answer_questions`
ADD CONSTRAINT `FK_projects_TO_short_answer_questions` FOREIGN KEY (`project_id`) REFERENCES `projects` (`project_id`);
ALTER TABLE `true_false_questions`
ADD CONSTRAINT `FK_projects_TO_true_false_questions` FOREIGN KEY (`project_id`) REFERENCES `projects` (`project_id`);
ALTER TABLE `matching_questions`
ADD CONSTRAINT `FK_projects_TO_matching_questions` FOREIGN KEY (`project_id`) REFERENCES `projects` (`project_id`);
ALTER TABLE `log_selection`
ADD CONSTRAINT `FK_projects_TO_log_selection` FOREIGN KEY (`project_id`) REFERENCES `projects` (`project_id`);
ALTER TABLE `generation_logs`
ADD CONSTRAINT `FK_projects_TO_generation_logs` FOREIGN KEY (`project_id`) REFERENCES `projects` (`project_id`);

-- project_source_config 참조
ALTER TABLE `multiple_choice_questions`
ADD CONSTRAINT `FK_project_source_config_TO_multiple_choice_questions` FOREIGN KEY (`config_id`) REFERENCES `project_source_config` (`config_id`);
ALTER TABLE `short_answer_questions`
ADD CONSTRAINT `FK_project_source_config_TO_short_answer_questions` FOREIGN KEY (`config_id`) REFERENCES `project_source_config` (`config_id`);
ALTER TABLE `true_false_questions`
ADD CONSTRAINT `FK_project_source_config_TO_true_false_questions` FOREIGN KEY (`config_id`) REFERENCES `project_source_config` (`config_id`);
ALTER TABLE `matching_questions`
ADD CONSTRAINT `FK_project_source_config_TO_matching_questions` FOREIGN KEY (`config_id`) REFERENCES `project_source_config` (`config_id`);
ALTER TABLE `generation_logs`
ADD CONSTRAINT `FK_project_source_config_TO_generation_logs` FOREIGN KEY (`config_id`) REFERENCES `project_source_config` (`config_id`);

-- batch_logs 참조
ALTER TABLE `multiple_choice_questions`
ADD CONSTRAINT `FK_batch_logs_TO_multiple_choice_questions` FOREIGN KEY (`batch_id`) REFERENCES `batch_logs` (`batch_id`);
ALTER TABLE `short_answer_questions`
ADD CONSTRAINT `FK_batch_logs_TO_short_answer_questions` FOREIGN KEY (`batch_id`) REFERENCES `batch_logs` (`batch_id`);
ALTER TABLE `true_false_questions`
ADD CONSTRAINT `FK_batch_logs_TO_true_false_questions` FOREIGN KEY (`batch_id`) REFERENCES `batch_logs` (`batch_id`);
ALTER TABLE `matching_questions`
ADD CONSTRAINT `FK_batch_logs_TO_matching_questions` FOREIGN KEY (`batch_id`) REFERENCES `batch_logs` (`batch_id`);

-- log_selection 참조
ALTER TABLE `log_download`
ADD CONSTRAINT `FK_log_selection_TO_log_download` FOREIGN KEY (`selection_id`) REFERENCES `log_selection` (`selection_id`);

SET FOREIGN_KEY_CHECKS = 1;
