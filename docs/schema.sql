-- ============================================
-- EduMark 作业批改系统 — DDL
-- 数据库: MySQL 8.0+
-- ============================================

CREATE DATABASE IF NOT EXISTS edumark
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE edumark;

-- ---------- 用户表 ----------
CREATE TABLE IF NOT EXISTS `user` (
    `id`          INT          NOT NULL AUTO_INCREMENT  COMMENT '主键',
    `account`     VARCHAR(64)  NOT NULL                 COMMENT '登录账号',
    `username`    VARCHAR(64)  NOT NULL                 COMMENT '显示用户名',
    `email`       VARCHAR(128) DEFAULT NULL             COMMENT '邮箱',
    `password`    VARCHAR(256) NOT NULL                 COMMENT 'bcrypt 密码哈希',
    `role`        VARCHAR(16)  NOT NULL DEFAULT 'student' COMMENT '角色: student/teacher/admin',
    `is_active`   TINYINT(1)   NOT NULL DEFAULT 1       COMMENT '账号是否启用',
    `create_time` DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_account` (`account`),
    UNIQUE KEY `uk_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ---------- 作业任务表 ----------
CREATE TABLE IF NOT EXISTS `task` (
    `id`          INT          NOT NULL AUTO_INCREMENT  COMMENT '内部自增主键',
    `task_id`     VARCHAR(36)  NOT NULL                 COMMENT '对外 UUID',
    `user_id`     INT          NOT NULL                 COMMENT '提交学生 FK → user.id',
    `subject`     VARCHAR(16)  DEFAULT NULL             COMMENT '科目: math/chinese/english',
    `grade`       VARCHAR(16)  DEFAULT NULL             COMMENT '年级',
    `mode`        VARCHAR(16)  NOT NULL                 COMMENT '识别模式: aliyun/bailian',
    `status`      VARCHAR(16)  NOT NULL DEFAULT 'pending' COMMENT '任务状态',
    `create_time` DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_task_id` (`task_id`),
    KEY `idx_user_id` (`user_id`),
    CONSTRAINT `fk_task_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='作业任务表';

-- ---------- 作业图片表 ----------
CREATE TABLE IF NOT EXISTS `image` (
    `id`          INT          NOT NULL AUTO_INCREMENT  COMMENT '主键',
    `task_id`     VARCHAR(36)  NOT NULL                 COMMENT '所属任务 FK → task.task_id',
    `url`         VARCHAR(512) NOT NULL                 COMMENT 'MinIO 图片路径',
    `create_time` DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_task_id` (`task_id`),
    CONSTRAINT `fk_image_task` FOREIGN KEY (`task_id`) REFERENCES `task` (`task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='作业图片表';

-- ---------- 题目表 ----------
CREATE TABLE IF NOT EXISTS `question` (
    `id`             INT          NOT NULL AUTO_INCREMENT  COMMENT '主键',
    `task_id`        VARCHAR(36)  NOT NULL                 COMMENT '所属任务 FK → task.task_id',
    `no`             VARCHAR(8)   NOT NULL                 COMMENT '题号 e.g. 1, 2a',
    `question_text`  TEXT         DEFAULT NULL             COMMENT '题目文本',
    `student_answer` TEXT         DEFAULT NULL             COMMENT '学生答案',
    `question_type`  VARCHAR(16)  DEFAULT NULL             COMMENT '题目类型',
    `create_time`    DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time`    DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_task_id` (`task_id`),
    CONSTRAINT `fk_question_task` FOREIGN KEY (`task_id`) REFERENCES `task` (`task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='题目表';

-- ---------- 题目块表 ----------
CREATE TABLE IF NOT EXISTS `block` (
    `id`          INT          NOT NULL AUTO_INCREMENT  COMMENT '主键',
    `question_id` INT          DEFAULT NULL             COMMENT '所属题目 FK → question.id',
    `url`         VARCHAR(512) NOT NULL                 COMMENT '裁剪子图 MinIO 路径',
    `x1`          DOUBLE       NOT NULL                 COMMENT '左上角 x（归一化 0-1）',
    `y1`          DOUBLE       NOT NULL                 COMMENT '左上角 y（归一化 0-1）',
    `x2`          DOUBLE       NOT NULL                 COMMENT '右下角 x（归一化 0-1）',
    `y2`          DOUBLE       NOT NULL                 COMMENT '右下角 y（归一化 0-1）',
    `create_time` DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_question_id` (`question_id`),
    CONSTRAINT `fk_block_question` FOREIGN KEY (`question_id`) REFERENCES `question` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='题目块表（切题坐标）';

-- ---------- 批改结果表 ----------
CREATE TABLE IF NOT EXISTS `correction` (
    `id`          INT           NOT NULL AUTO_INCREMENT  COMMENT '主键',
    `question_id` INT           NOT NULL                 COMMENT '题目 FK → question.id',
    `score`       DECIMAL(5,2)  NOT NULL                 COMMENT '得分',
    `result`      VARCHAR(16)   NOT NULL                 COMMENT '结果: correct/wrong/partial',
    `comment`     TEXT          DEFAULT NULL             COMMENT '评语',
    `analysis`    TEXT          DEFAULT NULL             COMMENT '解题分析',
    `create_time` DATETIME      DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_question_id` (`question_id`),
    CONSTRAINT `fk_correction_question` FOREIGN KEY (`question_id`) REFERENCES `question` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='批改结果表';

-- ---------- 知识文档表 ----------
CREATE TABLE IF NOT EXISTS `knowledge` (
    `id`          INT          NOT NULL AUTO_INCREMENT  COMMENT '主键',
    `user_id`     INT          NOT NULL                 COMMENT '上传教师 FK → user.id',
    `title`       VARCHAR(256) NOT NULL                 COMMENT '原始文件名',
    `url`         VARCHAR(512) NOT NULL                 COMMENT 'MinIO 对象路径',
    `subject`     VARCHAR(16)  DEFAULT NULL             COMMENT '学科',
    `grade`       VARCHAR(16)  DEFAULT NULL             COMMENT '年级',
    `status`      VARCHAR(16)  NOT NULL DEFAULT 'pending' COMMENT '解析状态: pending/parsing/completed/failed',
    `chunk`       INT          NOT NULL DEFAULT 0       COMMENT '知识块数量',
    `create_time` DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_user_id` (`user_id`),
    CONSTRAINT `fk_knowledge_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识文档表';

-- ---------- 题目-知识块关联表 ----------
CREATE TABLE IF NOT EXISTS `question_chunk` (
    `id`          INT          NOT NULL AUTO_INCREMENT  COMMENT '主键',
    `question_id` INT          NOT NULL                 COMMENT '题目 FK → question.id',
    `knowledge_id` INT         NOT NULL                 COMMENT '来源文档 FK → knowledge.id',
    `chunk_id`    VARCHAR(36)  NOT NULL                 COMMENT '向量库中知识块 UUID',
    `create_time` DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_question_id` (`question_id`),
    KEY `idx_knowledge_id` (`knowledge_id`),
    CONSTRAINT `fk_qc_question` FOREIGN KEY (`question_id`) REFERENCES `question` (`id`),
    CONSTRAINT `fk_qc_knowledge` FOREIGN KEY (`knowledge_id`) REFERENCES `knowledge` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='题目-知识块关联表';

-- ---------- 模型表 ----------
CREATE TABLE IF NOT EXISTS `model` (
    `id`   INT         NOT NULL AUTO_INCREMENT COMMENT '主键',
    `name` VARCHAR(64) NOT NULL                COMMENT '模型名称',
    `mode` INT         NOT NULL                COMMENT '作用: 1=提取题目, 2=批改题目',
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='模型表';

-- ---------- 用户配置表 ----------
CREATE TABLE IF NOT EXISTS `config` (
    `id`          INT          NOT NULL AUTO_INCREMENT  COMMENT '主键',
    `user_id`     INT          NOT NULL                 COMMENT '用户 FK → user.id',
    `rec_mode`    VARCHAR(16)  NOT NULL DEFAULT 'aliyun' COMMENT '识别模式: aliyun/bailian',
    `enable_enhance` TINYINT(1) NOT NULL DEFAULT 1    COMMENT '是否开启图片增强',
    `enable_knowledge` TINYINT(1) NOT NULL DEFAULT 1  COMMENT '是否开启知识库检索',
    `vl_model`    VARCHAR(64)  DEFAULT NULL             COMMENT '视觉模型名称',
    `gl_model`    VARCHAR(64)  DEFAULT NULL             COMMENT '批改模型名称',
    `create_time` DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_id` (`user_id`),
    CONSTRAINT `fk_config_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户配置表';

INSERT INTO edumark.model (id, name, mode) VALUES (1, 'qwen3.7-plus', 1);
INSERT INTO edumark.model (id, name, mode) VALUES (2, 'qwen3.6-max', 2);
INSERT INTO edumark.model (id, name, mode) VALUES (3, 'qwen3-vl-plus', 1);
INSERT INTO edumark.model (id, name, mode) VALUES (4, 'qwen3.5-plus', 1);
INSERT INTO edumark.model (id, name, mode) VALUES (5, 'qwen-plus', 2);
INSERT INTO edumark.model (id, name, mode) VALUES (6, 'deepseek-v4-flash', 2);
INSERT INTO edumark.model (id, name, mode) VALUES (7, 'qwen-vl-max', 1);

INSERT INTO edumark.user (id, account, username, email, password, role, is_active, create_time, update_time) VALUES (1, 'root', 'root', null, '$2b$12$XTThB.COmWVwn.fshAKvoe61vIr4vCzaI5qMBk2./o8n9XvUadPFe', 'admin', 1, null, null);
INSERT INTO edumark.user (id, account, username, email, password, role, is_active, create_time, update_time) VALUES (2, 'teacher', 'teacher', null, '$2b$12$k3jkX.L89LRhtk4cRjVzbOvJmwYHNIfqWEHQUOBlgQHzRFRmU/KKG', 'teacher', 1, null, null);
INSERT INTO edumark.user (id, account, username, email, password, role, is_active, create_time, update_time) VALUES (3, 'student01', 'student01', null, '$2b$12$JXDeU20MopMRh6DCl6SWlO6bPKM3vIrAfXJ1bx5ICcSz024mDHP3u', 'student', 1, null, null);
INSERT INTO edumark.user (id, account, username, email, password, role, is_active, create_time, update_time) VALUES (4, 'student02', 'student02', null, '$2b$12$4Isi.a1G9LOBQckjdu05tObY3vZSpg/5Bg69ZosgK0BHaYfN2bi.2', 'student', 1, null, null);

INSERT INTO edumark.config (id, user_id, rec_mode, enable_enhance, enable_knowledge, vl_model, gl_model, create_time, update_time) VALUES (1, 3, 'aliyun', 1, 1, null, null, null, null);
INSERT INTO edumark.config (id, user_id, rec_mode, enable_enhance, enable_knowledge, vl_model, gl_model, create_time, update_time) VALUES (2, 4, 'bailian', 0, 0, 'qwen3.7-plus', 'qwen-plus', null, '2026-06-03 01:52:23');
