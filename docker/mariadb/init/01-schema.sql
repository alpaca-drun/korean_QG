/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.11.15-MariaDB, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: KG_db
-- ------------------------------------------------------
-- Server version	10.11.15-MariaDB-ubu2204

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `achievement`
--

DROP TABLE IF EXISTS `achievement`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `achievement` (
  `ach_id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '성취기준 id',
  `code` varchar(50) DEFAULT NULL COMMENT '성취기준 코드 (예: 9국01-01)',
  `description` text DEFAULT NULL COMMENT '성취기준 내용',
  `evaluation_criteria` text DEFAULT NULL COMMENT '평가기준',
  PRIMARY KEY (`ach_id`)
) ENGINE=InnoDB AUTO_INCREMENT=17 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `batch_logs`
--

DROP TABLE IF EXISTS `batch_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `batch_logs` (
  `batch_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `input_token` int(11) DEFAULT NULL,
  `output_token` int(11) DEFAULT NULL,
  `total_duration` int(11) DEFAULT NULL,
  `temperature` float DEFAULT NULL,
  `top_p` float DEFAULT NULL,
  `top_k` float DEFAULT NULL,
  `model_name` varchar(50) DEFAULT NULL COMMENT 'LLM 모델 명',
  `total_attempts` int(11) DEFAULT NULL COMMENT '한번에 요청한 문항 수',
  `success_count` int(11) DEFAULT NULL COMMENT '생성 성공한 문항 수',
  `error_message` text DEFAULT NULL COMMENT '에러 발생 시 기록용',
  `created_at` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`batch_id`)
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `generation_logs`
--

DROP TABLE IF EXISTS `generation_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `generation_logs` (
  `generation_log_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `selection_id` bigint(20) DEFAULT NULL,
  `project_id` bigint(20) NOT NULL COMMENT '프로젝트 고유값',
  `question_type` varchar(50) DEFAULT NULL COMMENT '문항타입',
  `input_token` int(11) DEFAULT NULL COMMENT '사용한 총 인풋토큰',
  `output_token` int(11) DEFAULT NULL COMMENT '사용한 총 출력토큰',
  `model_name` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`generation_log_id`),
  KEY `FK_project_source_config_TO_generation_logs` (`selection_id`),
  CONSTRAINT `FK_project_source_config_TO_generation_logs` FOREIGN KEY (`selection_id`) REFERENCES `project_source_config` (`config_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `log_download`
--

DROP TABLE IF EXISTS `log_download`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `log_download` (
  `download_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `selection_id` bigint(20) DEFAULT NULL,
  `download_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`download_id`),
  KEY `FK_log_selection_TO_log_download` (`selection_id`),
  CONSTRAINT `FK_log_selection_TO_log_download` FOREIGN KEY (`selection_id`) REFERENCES `log_selection` (`selection_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `log_selection`
--

DROP TABLE IF EXISTS `log_selection`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `log_selection` (
  `selection_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `project_id` bigint(20) DEFAULT NULL,
  `JSON` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '선택한 문항 리스트' CHECK (json_valid(`JSON`)),
  `created_at` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`selection_id`),
  KEY `FK_projects_TO_log_selection` (`project_id`),
  CONSTRAINT `FK_projects_TO_log_selection` FOREIGN KEY (`project_id`) REFERENCES `projects` (`project_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `multiple_choice_questions`
--

DROP TABLE IF EXISTS `multiple_choice_questions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `multiple_choice_questions` (
  `question_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `config_id` bigint(20) DEFAULT NULL COMMENT '생성설정 아이디',
  `batch_id` bigint(20) NOT NULL COMMENT '배치 로그 아이디',
  `project_id` bigint(20) NOT NULL COMMENT '프로젝트 아이디',
  `question` longtext DEFAULT NULL COMMENT '문제 발문',
  `box_content` longtext DEFAULT NULL COMMENT '보기 박스에 들어갈 내용',
  `option1` longtext DEFAULT NULL COMMENT '객관식 답안1',
  `option2` longtext DEFAULT NULL COMMENT '객관식 답안2',
  `option3` longtext DEFAULT NULL COMMENT '객관식 답안3',
  `option4` longtext DEFAULT NULL COMMENT '객관식 답안4',
  `option5` longtext DEFAULT NULL COMMENT '객관식 답안 5',
  `answer` varchar(50) DEFAULT NULL COMMENT '정답 답안 번호 (여러개일 경우 ,로 구분)',
  `answer_explain` longtext DEFAULT NULL,
  `feedback_score` decimal(3,1) DEFAULT NULL COMMENT '0.5~10점 평가',
  `is_used` tinyint(1) DEFAULT NULL COMMENT '문항 사용여부',
  `llm_difficulty` varchar(50) DEFAULT NULL COMMENT 'LLM이 설정한난이도',
  `modified_difficulty` varchar(50) DEFAULT NULL COMMENT '변경한 난이도',
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `modified_passage` longtext DEFAULT NULL COMMENT '변형된 지문',
  PRIMARY KEY (`question_id`),
  KEY `FK_project_source_config_TO_multiple_choice_questions_1` (`config_id`),
  KEY `FK_batch_logs_TO_multiple_choice_questions_1` (`batch_id`),
  CONSTRAINT `FK_batch_logs_TO_multiple_choice_questions_1` FOREIGN KEY (`batch_id`) REFERENCES `batch_logs` (`batch_id`),
  CONSTRAINT `FK_project_source_config_TO_multiple_choice_questions_1` FOREIGN KEY (`config_id`) REFERENCES `project_source_config` (`config_id`)
) ENGINE=InnoDB AUTO_INCREMENT=215 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `passage_custom`
--

DROP TABLE IF EXISTS `passage_custom`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `passage_custom` (
  `custom_passage_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) NOT NULL,
  `scope_id` bigint(20) DEFAULT NULL COMMENT '원본 지문이 있는경우',
  `custom_title` varchar(100) DEFAULT NULL,
  `title` varchar(50) DEFAULT NULL,
  `auth` varchar(50) DEFAULT NULL,
  `context` longtext NOT NULL,
  `passage_id` bigint(20) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `is_use` int(11) DEFAULT NULL COMMENT '지문 사용 여부',
  PRIMARY KEY (`custom_passage_id`),
  KEY `FK_users_TO_custom_passage` (`user_id`),
  KEY `FK_project_scopes_TO_custom_passage` (`scope_id`),
  CONSTRAINT `FK_project_scopes_TO_custom_passage` FOREIGN KEY (`scope_id`) REFERENCES `project_scopes` (`scope_id`),
  CONSTRAINT `FK_users_TO_custom_passage` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `passages`
--

DROP TABLE IF EXISTS `passages`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `passages` (
  `passage_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `title` varchar(100) DEFAULT NULL,
  `context` longtext NOT NULL,
  `auth` varchar(50) DEFAULT NULL,
  `scope_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`passage_id`),
  KEY `FK_project_scopes_TO_passages` (`scope_id`),
  CONSTRAINT `FK_project_scopes_TO_passages` FOREIGN KEY (`scope_id`) REFERENCES `project_scopes` (`scope_id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `project_scopes`
--

DROP TABLE IF EXISTS `project_scopes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `project_scopes` (
  `scope_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `large_unit_id` int(11) DEFAULT NULL COMMENT '소단원 ID (API)',
  `large_unit_name` varchar(100) DEFAULT NULL,
  `small_unit_id` int(11) DEFAULT NULL COMMENT '외부/원본 지문 DB의 ID',
  `small_unit_name` varchar(100) DEFAULT NULL,
  `publisher_author` varchar(50) DEFAULT NULL COMMENT '출판사 및 저자',
  `grade` int(11) DEFAULT NULL,
  `semester` tinyint(4) DEFAULT NULL,
  `subject` varchar(50) DEFAULT NULL COMMENT '교과목',
  `learning_objective` text DEFAULT NULL COMMENT '학습목표',
  `learning_activity` text DEFAULT NULL COMMENT '학습활동',
  `learning_element` text DEFAULT NULL COMMENT '학습요소',
  `achievement_ids` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '성취기준 맵핑 [1, 5, 12])' CHECK (json_valid(`achievement_ids`)),
  `study_area` varchar(50) DEFAULT NULL COMMENT '영역(예: 맘하기듣기, 매체 등)',
  `school_level` varchar(50) DEFAULT '"중학교"' COMMENT '학교급(예:중학교)',
  PRIMARY KEY (`scope_id`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `project_source_config`
--

DROP TABLE IF EXISTS `project_source_config`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `project_source_config` (
  `config_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `project_id` bigint(20) DEFAULT NULL,
  `is_modified` tinyint(1) DEFAULT NULL COMMENT '지문 변형 여부',
  `passage_id` bigint(20) DEFAULT NULL COMMENT '원본소스를 사용했다면 기록',
  `custom_passage_id` bigint(20) DEFAULT NULL COMMENT '업로드한 지문 아이디',
  `question_type` varchar(50) DEFAULT NULL COMMENT '문항유형 (예 : 5지선다, 단답형)',
  `target_count` int(11) DEFAULT NULL COMMENT '요청한 문항 수',
  `pref_id` bigint(20) DEFAULT NULL COMMENT '부정어 리스트 아이디',
  `additional_prompt` text DEFAULT NULL COMMENT '추가 프롬프트',
  `use_ai_model` tinyint(1) DEFAULT NULL COMMENT 'ai 생성 요청했는지 여부',
  `stem_directive` text DEFAULT NULL COMMENT '발문 지시문 (예: ~로 알맞은 것은?)',
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp(),
  `input_tokens` int(11) DEFAULT NULL,
  `output_tokens` int(11) DEFAULT NULL,
  `model_name` varchar(50) DEFAULT NULL COMMENT 'llm 모델 명',
  PRIMARY KEY (`config_id`),
  KEY `FK_projects_TO_project_source_config` (`project_id`),
  CONSTRAINT `FK_projects_TO_project_source_config` FOREIGN KEY (`project_id`) REFERENCES `projects` (`project_id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `projects`
--

DROP TABLE IF EXISTS `projects`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `projects` (
  `project_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) NOT NULL,
  `scope_id` bigint(20) DEFAULT NULL,
  `project_name` varchar(100) NOT NULL,
  `status` enum('WRITING','GENERATING','COMPLETED') DEFAULT 'WRITING' COMMENT '작성중/생성중/완료',
  `is_deleted` tinyint(1) DEFAULT 0 COMMENT '삭제 여부',
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`project_id`),
  KEY `FK_users_TO_projects` (`user_id`),
  KEY `FK_project_scopes_TO_projects` (`scope_id`),
  CONSTRAINT `FK_project_scopes_TO_projects` FOREIGN KEY (`scope_id`) REFERENCES `project_scopes` (`scope_id`),
  CONSTRAINT `FK_users_TO_projects` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `question_modified_passage`
--

DROP TABLE IF EXISTS `question_modified_passage`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `question_modified_passage` (
  `modified_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `question_id` bigint(20) NOT NULL,
  `context` longtext DEFAULT NULL,
  PRIMARY KEY (`modified_id`),
  KEY `FK_mc_questions_TO_modified_passage` (`question_id`),
  CONSTRAINT `FK_mc_questions_TO_modified_passage` FOREIGN KEY (`question_id`) REFERENCES `multiple_choice_questions` (`question_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `short_answer_questions`
--

DROP TABLE IF EXISTS `short_answer_questions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `short_answer_questions` (
  `short_question_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `config_id` bigint(20) DEFAULT NULL,
  `batch_id` bigint(20) NOT NULL,
  `project_id` bigint(20) NOT NULL COMMENT '사용자 채택 여부 (다운로드 대상)',
  `question` longtext DEFAULT NULL COMMENT '문제 발문',
  `answer` varchar(50) DEFAULT NULL COMMENT '정답 답안 번호 (여러개일 경우 ,로 구분)',
  `answer_explain` longtext DEFAULT NULL,
  `is_used` tinyint(1) DEFAULT NULL,
  `box_content` longtext DEFAULT NULL COMMENT '보기 박스에 들어갈 내용',
  `feedback_score` decimal(3,1) DEFAULT NULL COMMENT '0.5~10점 평가',
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`short_question_id`),
  KEY `FK_batch_logs_TO_short_questions` (`batch_id`),
  KEY `FK_project_source_config_TO_short_answer_questions_1` (`config_id`),
  CONSTRAINT `FK_batch_logs_TO_short_questions` FOREIGN KEY (`batch_id`) REFERENCES `batch_logs` (`batch_id`),
  CONSTRAINT `FK_project_source_config_TO_short_answer_questions_1` FOREIGN KEY (`config_id`) REFERENCES `project_source_config` (`config_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `true_false_questions`
--

DROP TABLE IF EXISTS `true_false_questions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `true_false_questions` (
  `ox_question_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `config_id` bigint(20) DEFAULT NULL,
  `batch_id` bigint(20) NOT NULL,
  `project_id` bigint(20) NOT NULL COMMENT '사용자 채택 여부 (다운로드 대상)',
  `feedback_score` decimal(3,1) DEFAULT NULL COMMENT '0.5~10점 평가',
  `question` longtext DEFAULT NULL COMMENT '문제 발문',
  `answer` varchar(50) DEFAULT NULL COMMENT '정답 답안 번호 (여러개일 경우 ,로 구분)',
  `answer_explain` longtext DEFAULT NULL,
  `is_used` tinyint(1) DEFAULT NULL COMMENT '문항사용여부',
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`ox_question_id`),
  KEY `FK_batch_logs_TO_true_false_questions` (`batch_id`),
  KEY `FK_project_source_config_TO_true_false_questions_1` (`config_id`),
  CONSTRAINT `FK_batch_logs_TO_true_false_questions` FOREIGN KEY (`batch_id`) REFERENCES `batch_logs` (`batch_id`),
  CONSTRAINT `FK_project_source_config_TO_true_false_questions_1` FOREIGN KEY (`config_id`) REFERENCES `project_source_config` (`config_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_preferences`
--

DROP TABLE IF EXISTS `user_preferences`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_preferences` (
  `pref_id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT 'pk',
  `user_id` bigint(20) NOT NULL,
  `blocklist_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '부정어 리스트' CHECK (json_valid(`blocklist_json`)),
  PRIMARY KEY (`pref_id`),
  KEY `FK_users_TO_user_preferences` (`user_id`),
  CONSTRAINT `FK_users_TO_user_preferences` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `user_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `login_id` varchar(50) NOT NULL COMMENT '로그인 아이디',
  `password_hash` varchar(255) NOT NULL,
  `name` varchar(50) NOT NULL,
  `role` varchar(50) DEFAULT NULL,
  `subject` varchar(50) NOT NULL,
  `memo` varchar(50) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `email` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-01-21 16:38:10
