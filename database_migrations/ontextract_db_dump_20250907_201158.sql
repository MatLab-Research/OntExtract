--
-- PostgreSQL database dump
--

\restrict EUoSdvmUces6acmYtXfddHB3ZRkpC8zOdYrcArwV0TNe7XCSxtvdOdVkhHwo3UO

-- Dumped from database version 17.6 (Ubuntu 17.6-1.pgdg24.04+1)
-- Dumped by pg_dump version 17.6 (Ubuntu 17.6-1.pgdg24.04+1)

-- Started on 2025-09-07 20:11:58 EDT

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

DROP DATABASE ontextract_db;
--
-- TOC entry 4429 (class 1262 OID 17398)
-- Name: ontextract_db; Type: DATABASE; Schema: -; Owner: ontextract_user
--

CREATE DATABASE ontextract_db WITH TEMPLATE = template0 ENCODING = 'UTF8' LOCALE_PROVIDER = libc LOCALE = 'C.UTF-8';


ALTER DATABASE ontextract_db OWNER TO ontextract_user;

\unrestrict EUoSdvmUces6acmYtXfddHB3ZRkpC8zOdYrcArwV0TNe7XCSxtvdOdVkhHwo3UO
\connect ontextract_db
\restrict EUoSdvmUces6acmYtXfddHB3ZRkpC8zOdYrcArwV0TNe7XCSxtvdOdVkhHwo3UO

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 3 (class 3079 OID 17727)
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- TOC entry 4431 (class 0 OID 0)
-- Dependencies: 3
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


--
-- TOC entry 5 (class 3079 OID 19685)
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- TOC entry 4432 (class 0 OID 0)
-- Dependencies: 5
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- TOC entry 4 (class 3079 OID 17808)
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- TOC entry 4433 (class 0 OID 0)
-- Dependencies: 4
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- TOC entry 2 (class 3079 OID 17399)
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- TOC entry 4434 (class 0 OID 0)
-- Dependencies: 2
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


--
-- TOC entry 307 (class 1255 OID 49207)
-- Name: get_document_version_id(integer, integer); Type: FUNCTION; Schema: public; Owner: ontextract_user
--

CREATE FUNCTION public.get_document_version_id(base_document_id integer, target_version integer) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    version_document_id INTEGER;
BEGIN
    -- Find document ID for specific version
    SELECT d.id INTO version_document_id
    FROM documents d 
    WHERE ((d.id = base_document_id AND d.version_number = target_version)
        OR (d.source_document_id = base_document_id AND d.version_number = target_version))
    LIMIT 1;
    
    RETURN version_document_id;
END;
$$;


ALTER FUNCTION public.get_document_version_id(base_document_id integer, target_version integer) OWNER TO ontextract_user;

--
-- TOC entry 446 (class 1255 OID 49206)
-- Name: get_latest_document_version(integer); Type: FUNCTION; Schema: public; Owner: ontextract_user
--

CREATE FUNCTION public.get_latest_document_version(base_document_id integer) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    latest_version INTEGER;
BEGIN
    -- Find the highest version number for documents with same base ID
    SELECT MAX(d.version_number) INTO latest_version
    FROM documents d 
    WHERE (d.id = base_document_id OR d.source_document_id = base_document_id)
    OR (d.source_document_id IN (
        SELECT source_document_id FROM documents WHERE id = base_document_id
    ));
    
    RETURN COALESCE(latest_version, 1);
END;
$$;


ALTER FUNCTION public.get_latest_document_version(base_document_id integer) OWNER TO ontextract_user;

--
-- TOC entry 340 (class 1255 OID 49214)
-- Name: inherit_processing_data(integer, integer); Type: FUNCTION; Schema: public; Owner: ontextract_user
--

CREATE FUNCTION public.inherit_processing_data(source_document_id integer, target_document_id integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Copy embeddings from source to target
    INSERT INTO document_embeddings (
        document_id, term, period, embedding, 
        model_name, context_window, extraction_method, metadata, created_at
    )
    SELECT 
        target_document_id, term, period, embedding,
        model_name, context_window, extraction_method, metadata, CURRENT_TIMESTAMP
    FROM document_embeddings 
    WHERE document_id = source_document_id;

    -- Copy text segments from source to target  
    INSERT INTO text_segments (
        document_id, content, segment_type, segment_number,
        start_position, end_position, parent_segment_id, level,
        word_count, character_count, sentence_count, language, language_confidence,
        embedding, embedding_model, processed, processing_notes, topics, keywords,
        sentiment_score, complexity_score, created_at
    )
    SELECT 
        target_document_id, content, segment_type, segment_number,
        start_position, end_position, parent_segment_id, level,
        word_count, character_count, sentence_count, language, language_confidence,
        embedding, embedding_model, processed, processing_notes, topics, keywords,
        sentiment_score, complexity_score, CURRENT_TIMESTAMP
    FROM text_segments
    WHERE document_id = source_document_id;
    
END;
$$;


ALTER FUNCTION public.inherit_processing_data(source_document_id integer, target_document_id integer) OWNER TO ontextract_user;

--
-- TOC entry 351 (class 1255 OID 19748)
-- Name: update_context_anchor_frequency(); Type: FUNCTION; Schema: public; Owner: ontextract_user
--

CREATE FUNCTION public.update_context_anchor_frequency() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO context_anchors (anchor_term, frequency, first_used_in, last_used_in)
        VALUES ((SELECT anchor_term FROM context_anchors WHERE id = NEW.context_anchor_id), 1, NEW.term_version_id, NEW.term_version_id)
        ON CONFLICT (anchor_term) DO UPDATE SET
            frequency = context_anchors.frequency + 1,
            last_used_in = NEW.term_version_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE context_anchors SET frequency = frequency - 1 
        WHERE id = OLD.context_anchor_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;


ALTER FUNCTION public.update_context_anchor_frequency() OWNER TO ontextract_user;

--
-- TOC entry 457 (class 1255 OID 19746)
-- Name: update_terms_updated_at(); Type: FUNCTION; Schema: public; Owner: ontextract_user
--

CREATE FUNCTION public.update_terms_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_terms_updated_at() OWNER TO ontextract_user;

--
-- TOC entry 411 (class 1255 OID 43506)
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: ontextract_user
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_updated_at_column() OWNER TO ontextract_user;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 238 (class 1259 OID 19509)
-- Name: analysis_agents; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.analysis_agents (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    agent_type character varying(20) NOT NULL,
    name character varying(200) NOT NULL,
    description text,
    version character varying(50),
    algorithm_type character varying(100),
    model_parameters json,
    training_data character varying(200),
    expertise_domain character varying(100),
    institutional_affiliation character varying(200),
    created_at timestamp with time zone,
    is_active boolean,
    user_id integer,
    CONSTRAINT analysis_agents_agent_type_check CHECK (((agent_type)::text = ANY ((ARRAY['SoftwareAgent'::character varying, 'Person'::character varying, 'Organization'::character varying])::text[])))
);


ALTER TABLE public.analysis_agents OWNER TO ontextract_user;

--
-- TOC entry 241 (class 1259 OID 19576)
-- Name: context_anchors; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.context_anchors (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    anchor_term character varying(255) NOT NULL,
    frequency integer,
    first_used_in uuid,
    last_used_in uuid,
    created_at timestamp with time zone
);


ALTER TABLE public.context_anchors OWNER TO ontextract_user;

--
-- TOC entry 256 (class 1259 OID 43140)
-- Name: document_embeddings; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.document_embeddings (
    id integer NOT NULL,
    document_id integer,
    term character varying(200) NOT NULL,
    period integer,
    embedding public.vector(384),
    model_name character varying(100),
    context_window text,
    extraction_method character varying(50),
    metadata jsonb,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.document_embeddings OWNER TO ontextract_user;

--
-- TOC entry 255 (class 1259 OID 43139)
-- Name: document_embeddings_id_seq; Type: SEQUENCE; Schema: public; Owner: ontextract_user
--

CREATE SEQUENCE public.document_embeddings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.document_embeddings_id_seq OWNER TO ontextract_user;

--
-- TOC entry 4435 (class 0 OID 0)
-- Dependencies: 255
-- Name: document_embeddings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ontextract_user
--

ALTER SEQUENCE public.document_embeddings_id_seq OWNED BY public.document_embeddings.id;


--
-- TOC entry 279 (class 1259 OID 43772)
-- Name: document_processing_summary; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.document_processing_summary (
    id integer NOT NULL,
    document_id integer NOT NULL,
    processing_type character varying(50) NOT NULL,
    status character varying(20) NOT NULL,
    source_document_id integer,
    job_id integer,
    priority integer DEFAULT 1,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.document_processing_summary OWNER TO ontextract_user;

--
-- TOC entry 4436 (class 0 OID 0)
-- Dependencies: 279
-- Name: TABLE document_processing_summary; Type: COMMENT; Schema: public; Owner: ontextract_user
--

COMMENT ON TABLE public.document_processing_summary IS 'Efficient summary of processing capabilities available per document';


--
-- TOC entry 278 (class 1259 OID 43771)
-- Name: document_processing_summary_id_seq; Type: SEQUENCE; Schema: public; Owner: ontextract_user
--

CREATE SEQUENCE public.document_processing_summary_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.document_processing_summary_id_seq OWNER TO ontextract_user;

--
-- TOC entry 4437 (class 0 OID 0)
-- Dependencies: 278
-- Name: document_processing_summary_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ontextract_user
--

ALTER SEQUENCE public.document_processing_summary_id_seq OWNED BY public.document_processing_summary.id;


--
-- TOC entry 221 (class 1259 OID 17819)
-- Name: documents; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.documents (
    id integer NOT NULL,
    title character varying(200) NOT NULL,
    content_type character varying(20) NOT NULL,
    document_type character varying(20) NOT NULL,
    reference_subtype character varying(30),
    file_type character varying(10),
    original_filename character varying(255),
    file_path character varying(500),
    file_size integer,
    source_metadata json,
    content text,
    content_preview text,
    detected_language character varying(10),
    language_confidence double precision,
    status character varying(20) NOT NULL,
    word_count integer,
    character_count integer,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    processed_at timestamp without time zone,
    user_id integer NOT NULL,
    embedding character varying,
    parent_document_id integer,
    processing_metadata json,
    version_number integer DEFAULT 1,
    version_type character varying(20) DEFAULT 'original'::character varying,
    experiment_id integer,
    source_document_id integer,
    processing_notes text,
    CONSTRAINT check_version_number_positive CHECK ((version_number > 0)),
    CONSTRAINT check_version_type CHECK (((version_type)::text = ANY ((ARRAY['original'::character varying, 'processed'::character varying, 'experimental'::character varying, 'composite'::character varying])::text[])))
);


ALTER TABLE public.documents OWNER TO postgres;

--
-- TOC entry 4438 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN documents.processing_metadata; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.documents.processing_metadata IS 'General metadata for processing info, embeddings, and document analysis';


--
-- TOC entry 4439 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN documents.version_number; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.documents.version_number IS 'Sequential version number within a document family';


--
-- TOC entry 4440 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN documents.version_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.documents.version_type IS 'Type of version: original, processed, experimental';


--
-- TOC entry 4441 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN documents.experiment_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.documents.experiment_id IS 'Associated experiment (for experimental versions)';


--
-- TOC entry 4442 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN documents.source_document_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.documents.source_document_id IS 'Original document this version derives from';


--
-- TOC entry 4443 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN documents.processing_notes; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.documents.processing_notes IS 'Notes about processing operations that created this version';


--
-- TOC entry 225 (class 1259 OID 17833)
-- Name: experiments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.experiments (
    id integer NOT NULL,
    name character varying(200) NOT NULL,
    description text,
    experiment_type character varying(50) NOT NULL,
    configuration text,
    status character varying(20) NOT NULL,
    results text,
    results_summary text,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    started_at timestamp without time zone,
    completed_at timestamp without time zone,
    user_id integer NOT NULL
);


ALTER TABLE public.experiments OWNER TO postgres;

--
-- TOC entry 273 (class 1259 OID 43668)
-- Name: document_version_chains; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.document_version_chains AS
 SELECT COALESCE(d.source_document_id, d.id) AS root_document_id,
    d.id AS document_id,
    d.title,
    d.version_number,
    d.version_type,
    d.experiment_id,
    d.created_at,
    d.status,
    e.name AS experiment_name
   FROM (public.documents d
     LEFT JOIN public.experiments e ON ((d.experiment_id = e.id)))
  ORDER BY COALESCE(d.source_document_id, d.id), d.version_number;


ALTER VIEW public.document_version_chains OWNER TO postgres;

--
-- TOC entry 233 (class 1259 OID 17857)
-- Name: text_segments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.text_segments (
    id integer NOT NULL,
    content text NOT NULL,
    segment_type character varying(50),
    segment_number integer,
    start_position integer,
    end_position integer,
    parent_segment_id integer,
    level integer,
    word_count integer,
    character_count integer,
    sentence_count integer,
    language character varying(10),
    language_confidence double precision,
    embedding character varying,
    embedding_model character varying(100),
    processed boolean,
    processing_notes text,
    topics text,
    keywords text,
    sentiment_score double precision,
    complexity_score double precision,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    processed_at timestamp without time zone,
    document_id integer NOT NULL
);


ALTER TABLE public.text_segments OWNER TO postgres;

--
-- TOC entry 281 (class 1259 OID 49182)
-- Name: version_changelog; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.version_changelog (
    id integer NOT NULL,
    document_id integer NOT NULL,
    version_number integer NOT NULL,
    change_type character varying(50) NOT NULL,
    change_description text,
    previous_version integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_by integer NOT NULL,
    processing_metadata jsonb
);


ALTER TABLE public.version_changelog OWNER TO ontextract_user;

--
-- TOC entry 282 (class 1259 OID 49208)
-- Name: document_version_history; Type: VIEW; Schema: public; Owner: ontextract_user
--

CREATE VIEW public.document_version_history AS
 SELECT d.id,
    d.title,
    d.version_number,
    d.version_type,
    d.created_at AS version_created,
    d.source_document_id,
    COALESCE(d.source_document_id, d.id) AS base_document_id,
    ((d.version_number = 1) AND ((d.version_type)::text = 'original'::text)) AS is_base_document,
    COALESCE(e.embedding_count, (0)::bigint) AS embedding_count,
    COALESCE(s.segment_count, (0)::bigint) AS segment_count,
    array_agg(DISTINCT vc.change_type) FILTER (WHERE (vc.change_type IS NOT NULL)) AS changes_in_version,
    vc.change_description
   FROM (((public.documents d
     LEFT JOIN ( SELECT document_embeddings.document_id,
            count(*) AS embedding_count
           FROM public.document_embeddings
          GROUP BY document_embeddings.document_id) e ON ((d.id = e.document_id)))
     LEFT JOIN ( SELECT text_segments.document_id,
            count(*) AS segment_count
           FROM public.text_segments
          GROUP BY text_segments.document_id) s ON ((d.id = s.document_id)))
     LEFT JOIN public.version_changelog vc ON (((d.id = vc.document_id) AND (d.version_number = vc.version_number))))
  GROUP BY d.id, d.title, d.version_number, d.version_type, d.created_at, d.source_document_id, e.embedding_count, s.segment_count, vc.change_description
  ORDER BY COALESCE(d.source_document_id, d.id), d.version_number;


ALTER VIEW public.document_version_history OWNER TO ontextract_user;

--
-- TOC entry 222 (class 1259 OID 17824)
-- Name: documents_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.documents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.documents_id_seq OWNER TO postgres;

--
-- TOC entry 4448 (class 0 OID 0)
-- Dependencies: 222
-- Name: documents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.documents_id_seq OWNED BY public.documents.id;


--
-- TOC entry 246 (class 1259 OID 19802)
-- Name: domains; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.domains (
    id integer NOT NULL,
    uuid uuid NOT NULL,
    name character varying(255) NOT NULL,
    display_name character varying(255),
    namespace_uri text NOT NULL,
    description text,
    metadata json,
    is_active boolean,
    created_at timestamp with time zone,
    updated_at timestamp with time zone
);


ALTER TABLE public.domains OWNER TO ontextract_user;

--
-- TOC entry 245 (class 1259 OID 19801)
-- Name: domains_id_seq; Type: SEQUENCE; Schema: public; Owner: ontextract_user
--

CREATE SEQUENCE public.domains_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.domains_id_seq OWNER TO ontextract_user;

--
-- TOC entry 4450 (class 0 OID 0)
-- Dependencies: 245
-- Name: domains_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ontextract_user
--

ALTER SEQUENCE public.domains_id_seq OWNED BY public.domains.id;


--
-- TOC entry 223 (class 1259 OID 17825)
-- Name: experiment_documents; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.experiment_documents (
    experiment_id integer NOT NULL,
    document_id integer NOT NULL,
    added_at timestamp without time zone,
    processing_status character varying(20) DEFAULT 'pending'::character varying,
    processing_metadata json,
    embeddings_applied boolean DEFAULT false,
    embeddings_metadata json,
    segments_created boolean DEFAULT false,
    segments_metadata json,
    nlp_analysis_completed boolean DEFAULT false,
    nlp_results json,
    processed_at timestamp without time zone,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.experiment_documents OWNER TO postgres;

--
-- TOC entry 4451 (class 0 OID 0)
-- Dependencies: 223
-- Name: COLUMN experiment_documents.processing_status; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.experiment_documents.processing_status IS 'Status: pending, processing, completed, error';


--
-- TOC entry 4452 (class 0 OID 0)
-- Dependencies: 223
-- Name: COLUMN experiment_documents.processing_metadata; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.experiment_documents.processing_metadata IS 'General experiment-specific processing metadata';


--
-- TOC entry 4453 (class 0 OID 0)
-- Dependencies: 223
-- Name: COLUMN experiment_documents.embeddings_applied; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.experiment_documents.embeddings_applied IS 'Whether embeddings have been generated for this experiment';


--
-- TOC entry 4454 (class 0 OID 0)
-- Dependencies: 223
-- Name: COLUMN experiment_documents.embeddings_metadata; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.experiment_documents.embeddings_metadata IS 'Embedding model info and metrics for this experiment';


--
-- TOC entry 4455 (class 0 OID 0)
-- Dependencies: 223
-- Name: COLUMN experiment_documents.segments_created; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.experiment_documents.segments_created IS 'Whether document has been segmented for this experiment';


--
-- TOC entry 4456 (class 0 OID 0)
-- Dependencies: 223
-- Name: COLUMN experiment_documents.segments_metadata; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.experiment_documents.segments_metadata IS 'Segmentation parameters and results';


--
-- TOC entry 4457 (class 0 OID 0)
-- Dependencies: 223
-- Name: COLUMN experiment_documents.nlp_analysis_completed; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.experiment_documents.nlp_analysis_completed IS 'Whether NLP analysis is complete for this experiment';


--
-- TOC entry 4458 (class 0 OID 0)
-- Dependencies: 223
-- Name: COLUMN experiment_documents.nlp_results; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.experiment_documents.nlp_results IS 'Experiment-specific NLP analysis results';


--
-- TOC entry 268 (class 1259 OID 43413)
-- Name: experiment_documents_v2; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.experiment_documents_v2 (
    id integer NOT NULL,
    experiment_id integer NOT NULL,
    document_id integer NOT NULL,
    processing_status character varying(50) NOT NULL,
    embedding_model character varying(100),
    embedding_dimension integer,
    embeddings_applied boolean,
    embedding_metadata text,
    segmentation_method character varying(50),
    segment_size integer,
    segments_created boolean,
    segmentation_metadata text,
    nlp_analysis_completed boolean,
    nlp_tools_used text,
    processing_started_at timestamp without time zone,
    processing_completed_at timestamp without time zone,
    embeddings_generated_at timestamp without time zone,
    segmentation_completed_at timestamp without time zone,
    added_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.experiment_documents_v2 OWNER TO ontextract_user;

--
-- TOC entry 267 (class 1259 OID 43412)
-- Name: experiment_documents_v2_id_seq; Type: SEQUENCE; Schema: public; Owner: ontextract_user
--

CREATE SEQUENCE public.experiment_documents_v2_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.experiment_documents_v2_id_seq OWNER TO ontextract_user;

--
-- TOC entry 4460 (class 0 OID 0)
-- Dependencies: 267
-- Name: experiment_documents_v2_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ontextract_user
--

ALTER SEQUENCE public.experiment_documents_v2_id_seq OWNED BY public.experiment_documents_v2.id;


--
-- TOC entry 224 (class 1259 OID 17828)
-- Name: experiment_references; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.experiment_references (
    experiment_id integer NOT NULL,
    reference_id integer NOT NULL,
    include_in_analysis boolean,
    added_at timestamp without time zone,
    notes text
);


ALTER TABLE public.experiment_references OWNER TO postgres;

--
-- TOC entry 226 (class 1259 OID 17838)
-- Name: experiments_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.experiments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.experiments_id_seq OWNER TO postgres;

--
-- TOC entry 4462 (class 0 OID 0)
-- Dependencies: 226
-- Name: experiments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.experiments_id_seq OWNED BY public.experiments.id;


--
-- TOC entry 227 (class 1259 OID 17839)
-- Name: extracted_entities; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.extracted_entities (
    id integer NOT NULL,
    entity_text character varying(500) NOT NULL,
    entity_type character varying(100) NOT NULL,
    entity_subtype character varying(100),
    context_before character varying(200),
    context_after character varying(200),
    sentence text,
    start_position integer,
    end_position integer,
    paragraph_number integer,
    sentence_number integer,
    confidence_score double precision,
    extraction_method character varying(50),
    properties text,
    language character varying(10),
    normalized_form character varying(500),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    processing_job_id integer NOT NULL,
    text_segment_id integer
);


ALTER TABLE public.extracted_entities OWNER TO postgres;

--
-- TOC entry 228 (class 1259 OID 17844)
-- Name: extracted_entities_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.extracted_entities_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.extracted_entities_id_seq OWNER TO postgres;

--
-- TOC entry 4465 (class 0 OID 0)
-- Dependencies: 228
-- Name: extracted_entities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.extracted_entities_id_seq OWNED BY public.extracted_entities.id;


--
-- TOC entry 240 (class 1259 OID 19557)
-- Name: fuzziness_adjustments; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.fuzziness_adjustments (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    term_version_id uuid NOT NULL,
    original_score numeric(4,3) NOT NULL,
    adjusted_score numeric(4,3) NOT NULL,
    adjustment_reason text NOT NULL,
    adjusted_by integer,
    created_at timestamp with time zone
);


ALTER TABLE public.fuzziness_adjustments OWNER TO ontextract_user;

--
-- TOC entry 265 (class 1259 OID 43347)
-- Name: learning_patterns; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.learning_patterns (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    pattern_name character varying(100) NOT NULL,
    pattern_type character varying(50) NOT NULL,
    context_signature character varying(200) NOT NULL,
    conditions jsonb NOT NULL,
    recommendations jsonb NOT NULL,
    confidence numeric(4,3) NOT NULL,
    derived_from_feedback uuid,
    researcher_authority jsonb,
    times_applied integer DEFAULT 0,
    success_rate numeric(4,3),
    last_applied timestamp with time zone,
    pattern_status character varying(20) DEFAULT 'active'::character varying,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT learning_patterns_confidence_check CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))),
    CONSTRAINT learning_patterns_success_rate_check CHECK (((success_rate >= (0)::numeric) AND (success_rate <= (1)::numeric))),
    CONSTRAINT pattern_status_check CHECK (((pattern_status)::text = ANY ((ARRAY['active'::character varying, 'deprecated'::character varying, 'under_review'::character varying, 'experimental'::character varying])::text[]))),
    CONSTRAINT pattern_type_check CHECK (((pattern_type)::text = ANY ((ARRAY['avoidance'::character varying, 'preference'::character varying, 'enhancement'::character varying, 'domain_specific'::character varying])::text[])))
);


ALTER TABLE public.learning_patterns OWNER TO ontextract_user;

--
-- TOC entry 4467 (class 0 OID 0)
-- Dependencies: 265
-- Name: TABLE learning_patterns; Type: COMMENT; Schema: public; Owner: ontextract_user
--

COMMENT ON TABLE public.learning_patterns IS 'Codified learning patterns derived from researcher feedback';


--
-- TOC entry 4468 (class 0 OID 0)
-- Dependencies: 265
-- Name: COLUMN learning_patterns.context_signature; Type: COMMENT; Schema: public; Owner: ontextract_user
--

COMMENT ON COLUMN public.learning_patterns.context_signature IS 'Signature for matching similar decision contexts';


--
-- TOC entry 4469 (class 0 OID 0)
-- Dependencies: 265
-- Name: COLUMN learning_patterns.researcher_authority; Type: COMMENT; Schema: public; Owner: ontextract_user
--

COMMENT ON COLUMN public.learning_patterns.researcher_authority IS 'Authority assessment of source researcher for weighting';


--
-- TOC entry 263 (class 1259 OID 43301)
-- Name: multi_model_consensus; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.multi_model_consensus (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    orchestration_decision_id uuid NOT NULL,
    validation_type character varying(50) DEFAULT 'multi_model_consensus'::character varying,
    models_involved text[],
    consensus_method character varying(50),
    model_responses jsonb,
    model_confidence_scores jsonb,
    model_agreement_matrix jsonb,
    consensus_reached boolean,
    consensus_confidence numeric(4,3),
    final_decision jsonb,
    disagreement_areas jsonb,
    started_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    completed_at timestamp with time zone,
    total_processing_time_ms integer,
    CONSTRAINT multi_model_consensus_consensus_confidence_check CHECK (((consensus_confidence >= (0)::numeric) AND (consensus_confidence <= (1)::numeric)))
);


ALTER TABLE public.multi_model_consensus OWNER TO ontextract_user;

--
-- TOC entry 4470 (class 0 OID 0)
-- Dependencies: 263
-- Name: TABLE multi_model_consensus; Type: COMMENT; Schema: public; Owner: ontextract_user
--

COMMENT ON TABLE public.multi_model_consensus IS 'Multi-model validation and consensus decision logging';


--
-- TOC entry 4471 (class 0 OID 0)
-- Dependencies: 263
-- Name: COLUMN multi_model_consensus.model_agreement_matrix; Type: COMMENT; Schema: public; Owner: ontextract_user
--

COMMENT ON COLUMN public.multi_model_consensus.model_agreement_matrix IS 'Pairwise agreement scores between models';


--
-- TOC entry 4472 (class 0 OID 0)
-- Dependencies: 263
-- Name: COLUMN multi_model_consensus.disagreement_areas; Type: COMMENT; Schema: public; Owner: ontextract_user
--

COMMENT ON COLUMN public.multi_model_consensus.disagreement_areas IS 'Specific areas where models disagreed';


--
-- TOC entry 258 (class 1259 OID 43172)
-- Name: oed_definitions; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.oed_definitions (
    id uuid NOT NULL,
    term_id uuid NOT NULL,
    definition_number character varying(10),
    first_cited_year integer,
    last_cited_year integer,
    part_of_speech character varying(30),
    domain_label character varying(100),
    status character varying(20),
    quotation_count integer,
    sense_frequency_rank integer,
    historical_period character varying(50),
    period_start_year integer,
    period_end_year integer,
    generated_at_time timestamp with time zone,
    was_attributed_to character varying(100),
    was_derived_from character varying(200),
    derivation_type character varying(50),
    definition_confidence character varying(20),
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    definition_excerpt character varying(300),
    oed_sense_id character varying(100),
    oed_url character varying(500),
    CONSTRAINT oed_definitions_definition_confidence_check CHECK (((definition_confidence)::text = ANY ((ARRAY['high'::character varying, 'medium'::character varying, 'low'::character varying])::text[]))),
    CONSTRAINT oed_definitions_status_check CHECK (((status)::text = ANY ((ARRAY['current'::character varying, 'historical'::character varying, 'obsolete'::character varying])::text[])))
);


ALTER TABLE public.oed_definitions OWNER TO ontextract_user;

--
-- TOC entry 257 (class 1259 OID 43159)
-- Name: oed_etymology; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.oed_etymology (
    id uuid NOT NULL,
    term_id uuid NOT NULL,
    etymology_text text,
    origin_language character varying(50),
    first_recorded_year integer,
    etymology_confidence character varying(20),
    language_family json,
    root_analysis json,
    morphology json,
    generated_at_time timestamp with time zone,
    was_attributed_to character varying(100),
    was_derived_from character varying(200),
    derivation_type character varying(50),
    source_version character varying(50),
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    CONSTRAINT oed_etymology_etymology_confidence_check CHECK (((etymology_confidence)::text = ANY ((ARRAY['high'::character varying, 'medium'::character varying, 'low'::character varying])::text[])))
);


ALTER TABLE public.oed_etymology OWNER TO ontextract_user;

--
-- TOC entry 259 (class 1259 OID 43188)
-- Name: oed_historical_stats; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.oed_historical_stats (
    id uuid NOT NULL,
    term_id uuid NOT NULL,
    time_period character varying(50) NOT NULL,
    start_year integer NOT NULL,
    end_year integer NOT NULL,
    definition_count integer,
    sense_count integer,
    quotation_span_years integer,
    earliest_quotation_year integer,
    latest_quotation_year integer,
    semantic_stability_score numeric(4,3),
    domain_shift_indicator boolean,
    part_of_speech_changes json,
    started_at_time timestamp with time zone,
    ended_at_time timestamp with time zone,
    was_associated_with character varying(100),
    used_entity json,
    generated_entity character varying(200),
    oed_edition character varying(50),
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    CONSTRAINT oed_historical_stats_semantic_stability_score_check CHECK (((semantic_stability_score >= (0)::numeric) AND (semantic_stability_score <= (1)::numeric)))
);


ALTER TABLE public.oed_historical_stats OWNER TO ontextract_user;

--
-- TOC entry 260 (class 1259 OID 43204)
-- Name: oed_quotation_summaries; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.oed_quotation_summaries (
    id uuid NOT NULL,
    term_id uuid NOT NULL,
    oed_definition_id uuid,
    quotation_year integer,
    author_name character varying(200),
    work_title character varying(300),
    domain_context character varying(100),
    usage_type character varying(50),
    has_technical_usage boolean,
    represents_semantic_shift boolean,
    chronological_rank integer,
    generated_at_time timestamp with time zone,
    was_attributed_to character varying(100),
    was_derived_from character varying(200),
    derivation_type character varying(50),
    created_at timestamp with time zone,
    updated_at timestamp with time zone
);


ALTER TABLE public.oed_quotation_summaries OWNER TO ontextract_user;

--
-- TOC entry 250 (class 1259 OID 19826)
-- Name: ontologies; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.ontologies (
    id integer NOT NULL,
    uuid uuid NOT NULL,
    domain_id integer,
    name character varying(255) NOT NULL,
    base_uri text NOT NULL,
    description text,
    is_base boolean,
    is_editable boolean,
    parent_ontology_id integer,
    ontology_type character varying(20),
    metadata json,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone
);


ALTER TABLE public.ontologies OWNER TO ontextract_user;

--
-- TOC entry 249 (class 1259 OID 19825)
-- Name: ontologies_id_seq; Type: SEQUENCE; Schema: public; Owner: ontextract_user
--

CREATE SEQUENCE public.ontologies_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ontologies_id_seq OWNER TO ontextract_user;

--
-- TOC entry 4473 (class 0 OID 0)
-- Dependencies: 249
-- Name: ontologies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ontextract_user
--

ALTER SEQUENCE public.ontologies_id_seq OWNED BY public.ontologies.id;


--
-- TOC entry 254 (class 1259 OID 19863)
-- Name: ontology_entities; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.ontology_entities (
    id integer NOT NULL,
    ontology_id integer NOT NULL,
    entity_type character varying(50) NOT NULL,
    uri text NOT NULL,
    label character varying(255),
    comment text,
    parent_uri text,
    domain json,
    range json,
    properties json,
    embedding public.vector(384),
    created_at timestamp without time zone
);


ALTER TABLE public.ontology_entities OWNER TO ontextract_user;

--
-- TOC entry 253 (class 1259 OID 19862)
-- Name: ontology_entities_id_seq; Type: SEQUENCE; Schema: public; Owner: ontextract_user
--

CREATE SEQUENCE public.ontology_entities_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ontology_entities_id_seq OWNER TO ontextract_user;

--
-- TOC entry 4474 (class 0 OID 0)
-- Dependencies: 253
-- Name: ontology_entities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ontextract_user
--

ALTER SEQUENCE public.ontology_entities_id_seq OWNED BY public.ontology_entities.id;


--
-- TOC entry 229 (class 1259 OID 17845)
-- Name: ontology_mappings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ontology_mappings (
    id integer NOT NULL,
    ontology_uri character varying(500) NOT NULL,
    concept_label character varying(200) NOT NULL,
    concept_definition text,
    parent_concepts text,
    child_concepts text,
    related_concepts text,
    mapping_confidence double precision,
    mapping_method character varying(50),
    mapping_source character varying(100),
    semantic_type character varying(100),
    domain character varying(100),
    properties text,
    is_verified boolean,
    verified_by character varying(100),
    verification_notes text,
    alternative_mappings text,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    verified_at timestamp without time zone,
    extracted_entity_id integer NOT NULL
);


ALTER TABLE public.ontology_mappings OWNER TO postgres;

--
-- TOC entry 230 (class 1259 OID 17850)
-- Name: ontology_mappings_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ontology_mappings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ontology_mappings_id_seq OWNER TO postgres;

--
-- TOC entry 4476 (class 0 OID 0)
-- Dependencies: 230
-- Name: ontology_mappings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ontology_mappings_id_seq OWNED BY public.ontology_mappings.id;


--
-- TOC entry 252 (class 1259 OID 19847)
-- Name: ontology_versions; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.ontology_versions (
    id integer NOT NULL,
    ontology_id integer NOT NULL,
    version_number integer NOT NULL,
    version_tag character varying(50),
    content text NOT NULL,
    content_hash character varying(64),
    change_summary text,
    created_by character varying(255),
    created_at timestamp with time zone NOT NULL,
    is_current boolean,
    is_draft boolean,
    workflow_status character varying(20),
    metadata json
);


ALTER TABLE public.ontology_versions OWNER TO ontextract_user;

--
-- TOC entry 251 (class 1259 OID 19846)
-- Name: ontology_versions_id_seq; Type: SEQUENCE; Schema: public; Owner: ontextract_user
--

CREATE SEQUENCE public.ontology_versions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ontology_versions_id_seq OWNER TO ontextract_user;

--
-- TOC entry 4478 (class 0 OID 0)
-- Dependencies: 251
-- Name: ontology_versions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ontextract_user
--

ALTER SEQUENCE public.ontology_versions_id_seq OWNED BY public.ontology_versions.id;


--
-- TOC entry 261 (class 1259 OID 43237)
-- Name: orchestration_decisions; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.orchestration_decisions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    activity_type character varying(50) DEFAULT 'llm_orchestration'::character varying NOT NULL,
    started_at_time timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    ended_at_time timestamp with time zone,
    activity_status character varying(20) DEFAULT 'completed'::character varying,
    document_id integer,
    experiment_id integer,
    term_text character varying(255),
    input_metadata jsonb,
    document_characteristics jsonb,
    orchestrator_provider character varying(50),
    orchestrator_model character varying(100),
    orchestrator_prompt text,
    orchestrator_response text,
    orchestrator_response_time_ms integer,
    selected_tools text[],
    embedding_model character varying(100),
    processing_strategy character varying(50),
    expected_runtime_seconds integer,
    decision_confidence numeric(4,3),
    reasoning_summary text,
    decision_factors jsonb,
    decision_validated boolean,
    actual_runtime_seconds integer,
    tool_execution_success jsonb,
    was_associated_with uuid,
    used_entity uuid,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    created_by integer,
    CONSTRAINT orchestration_decisions_activity_status_check CHECK (((activity_status)::text = ANY ((ARRAY['running'::character varying, 'completed'::character varying, 'error'::character varying, 'timeout'::character varying])::text[]))),
    CONSTRAINT orchestration_decisions_decision_confidence_check CHECK (((decision_confidence >= (0)::numeric) AND (decision_confidence <= (1)::numeric)))
);


ALTER TABLE public.orchestration_decisions OWNER TO ontextract_user;

--
-- TOC entry 4479 (class 0 OID 0)
-- Dependencies: 261
-- Name: TABLE orchestration_decisions; Type: COMMENT; Schema: public; Owner: ontextract_user
--

COMMENT ON TABLE public.orchestration_decisions IS 'PROV-O compliant logging of LLM orchestration decisions for tool selection and coordination';


--
-- TOC entry 4480 (class 0 OID 0)
-- Dependencies: 261
-- Name: COLUMN orchestration_decisions.input_metadata; Type: COMMENT; Schema: public; Owner: ontextract_user
--

COMMENT ON COLUMN public.orchestration_decisions.input_metadata IS 'Document metadata that influenced tool selection (year, domain, format, length)';


--
-- TOC entry 4481 (class 0 OID 0)
-- Dependencies: 261
-- Name: COLUMN orchestration_decisions.decision_factors; Type: COMMENT; Schema: public; Owner: ontextract_user
--

COMMENT ON COLUMN public.orchestration_decisions.decision_factors IS 'Structured reasoning components for decision analysis';


--
-- TOC entry 4482 (class 0 OID 0)
-- Dependencies: 261
-- Name: COLUMN orchestration_decisions.tool_execution_success; Type: COMMENT; Schema: public; Owner: ontextract_user
--

COMMENT ON COLUMN public.orchestration_decisions.tool_execution_success IS 'Per-tool success rates and validation results';


--
-- TOC entry 264 (class 1259 OID 43319)
-- Name: orchestration_feedback; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.orchestration_feedback (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    orchestration_decision_id uuid NOT NULL,
    researcher_id integer NOT NULL,
    researcher_expertise jsonb,
    feedback_type character varying(50) NOT NULL,
    feedback_scope character varying(50),
    original_decision jsonb,
    researcher_preference jsonb,
    agreement_level character varying(20),
    confidence_assessment numeric(4,3),
    reasoning text NOT NULL,
    domain_specific_factors jsonb,
    suggested_tools text[],
    suggested_embedding_model character varying(100),
    suggested_processing_strategy character varying(50),
    alternative_reasoning text,
    feedback_status character varying(20) DEFAULT 'pending'::character varying,
    integration_notes text,
    subsequent_decisions_influenced integer DEFAULT 0,
    improvement_verified boolean,
    verification_notes text,
    provided_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    reviewed_at timestamp with time zone,
    integrated_at timestamp with time zone,
    CONSTRAINT agreement_level_check CHECK (((agreement_level)::text = ANY ((ARRAY['strongly_agree'::character varying, 'agree'::character varying, 'neutral'::character varying, 'disagree'::character varying, 'strongly_disagree'::character varying])::text[]))),
    CONSTRAINT feedback_status_check CHECK (((feedback_status)::text = ANY ((ARRAY['pending'::character varying, 'reviewed'::character varying, 'integrated'::character varying, 'rejected'::character varying, 'obsolete'::character varying])::text[]))),
    CONSTRAINT feedback_type_check CHECK (((feedback_type)::text = ANY ((ARRAY['correction'::character varying, 'enhancement'::character varying, 'validation'::character varying, 'clarification'::character varying])::text[]))),
    CONSTRAINT orchestration_feedback_confidence_assessment_check CHECK (((confidence_assessment >= (0)::numeric) AND (confidence_assessment <= (1)::numeric)))
);


ALTER TABLE public.orchestration_feedback OWNER TO ontextract_user;

--
-- TOC entry 4483 (class 0 OID 0)
-- Dependencies: 264
-- Name: TABLE orchestration_feedback; Type: COMMENT; Schema: public; Owner: ontextract_user
--

COMMENT ON TABLE public.orchestration_feedback IS 'Researcher feedback on orchestration decisions for continuous improvement';


--
-- TOC entry 4484 (class 0 OID 0)
-- Dependencies: 264
-- Name: COLUMN orchestration_feedback.researcher_expertise; Type: COMMENT; Schema: public; Owner: ontextract_user
--

COMMENT ON COLUMN public.orchestration_feedback.researcher_expertise IS 'Researcher expertise profile for weighting feedback authority';


--
-- TOC entry 4485 (class 0 OID 0)
-- Dependencies: 264
-- Name: COLUMN orchestration_feedback.domain_specific_factors; Type: COMMENT; Schema: public; Owner: ontextract_user
--

COMMENT ON COLUMN public.orchestration_feedback.domain_specific_factors IS 'Domain knowledge that LLM missed in original decision';


--
-- TOC entry 266 (class 1259 OID 43371)
-- Name: orchestration_overrides; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.orchestration_overrides (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    orchestration_decision_id uuid NOT NULL,
    researcher_id integer NOT NULL,
    override_type character varying(50) NOT NULL,
    original_decision jsonb NOT NULL,
    overridden_decision jsonb NOT NULL,
    justification text NOT NULL,
    expert_knowledge_applied jsonb,
    override_applied boolean DEFAULT false,
    execution_results jsonb,
    performance_comparison jsonb,
    applied_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT override_type_check CHECK (((override_type)::text = ANY ((ARRAY['full_replacement'::character varying, 'tool_addition'::character varying, 'tool_removal'::character varying, 'model_change'::character varying, 'strategy_change'::character varying])::text[])))
);


ALTER TABLE public.orchestration_overrides OWNER TO ontextract_user;

--
-- TOC entry 4486 (class 0 OID 0)
-- Dependencies: 266
-- Name: TABLE orchestration_overrides; Type: COMMENT; Schema: public; Owner: ontextract_user
--

COMMENT ON TABLE public.orchestration_overrides IS 'Manual overrides applied by researchers to specific orchestration decisions';


--
-- TOC entry 231 (class 1259 OID 17851)
-- Name: processing_jobs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.processing_jobs (
    id integer NOT NULL,
    job_type character varying(50) NOT NULL,
    job_name character varying(100),
    provider character varying(20),
    model character varying(50),
    parameters text,
    status character varying(20) NOT NULL,
    progress_percent integer,
    current_step character varying(100),
    total_steps integer,
    result_data text,
    result_summary text,
    error_message text,
    error_details text,
    retry_count integer,
    max_retries integer,
    tokens_used integer,
    processing_time double precision,
    cost_estimate double precision,
    created_at timestamp without time zone NOT NULL,
    started_at timestamp without time zone,
    completed_at timestamp without time zone,
    updated_at timestamp without time zone,
    user_id integer NOT NULL,
    document_id integer NOT NULL,
    parent_job_id integer
);


ALTER TABLE public.processing_jobs OWNER TO postgres;

--
-- TOC entry 232 (class 1259 OID 17856)
-- Name: processing_jobs_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.processing_jobs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.processing_jobs_id_seq OWNER TO postgres;

--
-- TOC entry 4488 (class 0 OID 0)
-- Dependencies: 232
-- Name: processing_jobs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.processing_jobs_id_seq OWNED BY public.processing_jobs.id;


--
-- TOC entry 270 (class 1259 OID 43560)
-- Name: prov_activities; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.prov_activities (
    activity_id uuid DEFAULT gen_random_uuid() NOT NULL,
    activity_type character varying(100) NOT NULL,
    startedattime timestamp with time zone,
    endedattime timestamp with time zone,
    wasassociatedwith uuid,
    activity_parameters jsonb DEFAULT '{}'::jsonb,
    activity_status character varying(20) DEFAULT 'active'::character varying,
    activity_metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT prov_activities_activity_status_check CHECK (((activity_status)::text = ANY ((ARRAY['active'::character varying, 'completed'::character varying, 'failed'::character varying])::text[]))),
    CONSTRAINT valid_activity_duration CHECK (((startedattime IS NULL) OR (endedattime IS NULL) OR (startedattime <= endedattime)))
);


ALTER TABLE public.prov_activities OWNER TO ontextract_user;

--
-- TOC entry 269 (class 1259 OID 43548)
-- Name: prov_agents; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.prov_agents (
    agent_id uuid DEFAULT gen_random_uuid() NOT NULL,
    agent_type character varying(20) NOT NULL,
    foaf_name character varying(255),
    foaf_givenname character varying(255),
    foaf_mbox character varying(255),
    foaf_homepage character varying(500),
    agent_metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT prov_agents_agent_type_check CHECK (((agent_type)::text = ANY ((ARRAY['Person'::character varying, 'Organization'::character varying, 'SoftwareAgent'::character varying])::text[])))
);


ALTER TABLE public.prov_agents OWNER TO ontextract_user;

--
-- TOC entry 271 (class 1259 OID 43579)
-- Name: prov_entities; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.prov_entities (
    entity_id uuid DEFAULT gen_random_uuid() NOT NULL,
    entity_type character varying(100) NOT NULL,
    generatedattime timestamp with time zone,
    invalidatedattime timestamp with time zone,
    wasgeneratedby uuid,
    wasattributedto uuid,
    wasderivedfrom uuid,
    entity_value jsonb DEFAULT '{}'::jsonb NOT NULL,
    entity_metadata jsonb DEFAULT '{}'::jsonb,
    character_start integer,
    character_end integer,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT must_have_generation_provenance CHECK ((wasgeneratedby IS NOT NULL)),
    CONSTRAINT valid_character_positions CHECK ((((character_start IS NULL) AND (character_end IS NULL)) OR ((character_start IS NOT NULL) AND (character_end IS NOT NULL) AND (character_start <= character_end))))
);


ALTER TABLE public.prov_entities OWNER TO ontextract_user;

--
-- TOC entry 272 (class 1259 OID 43607)
-- Name: prov_relationships; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.prov_relationships (
    relationship_id uuid DEFAULT gen_random_uuid() NOT NULL,
    relationship_type character varying(50) NOT NULL,
    subject_id uuid NOT NULL,
    subject_type character varying(20) NOT NULL,
    object_id uuid NOT NULL,
    object_type character varying(20) NOT NULL,
    relationship_metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT prov_relationships_object_type_check CHECK (((object_type)::text = ANY ((ARRAY['Agent'::character varying, 'Activity'::character varying, 'Entity'::character varying])::text[]))),
    CONSTRAINT prov_relationships_relationship_type_check CHECK (((relationship_type)::text = ANY (ARRAY[('wasGeneratedBy'::character varying)::text, ('wasAssociatedWith'::character varying)::text, ('wasDerivedFrom'::character varying)::text, ('wasInformedBy'::character varying)::text, ('actedOnBehalfOf'::character varying)::text, ('wasAttributedTo'::character varying)::text, ('used'::character varying)::text, ('wasStartedBy'::character varying)::text, ('wasEndedBy'::character varying)::text, ('wasQuotedFrom'::character varying)::text, ('wasRevisionOf'::character varying)::text, ('hadPrimarySource'::character varying)::text, ('alternateOf'::character varying)::text, ('specializationOf'::character varying)::text]))),
    CONSTRAINT prov_relationships_subject_type_check CHECK (((subject_type)::text = ANY ((ARRAY['Agent'::character varying, 'Activity'::character varying, 'Entity'::character varying])::text[])))
);


ALTER TABLE public.prov_relationships OWNER TO ontextract_user;

--
-- TOC entry 277 (class 1259 OID 43690)
-- Name: provenance_activities; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.provenance_activities (
    id integer NOT NULL,
    prov_id character varying(255) NOT NULL,
    prov_type character varying(100) NOT NULL,
    prov_label character varying(500),
    started_at_time timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    ended_at_time timestamp without time zone,
    was_associated_with character varying(255),
    used_plan character varying(255),
    processing_job_id integer,
    experiment_id integer,
    activity_type character varying(50),
    activity_metadata jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.provenance_activities OWNER TO postgres;

--
-- TOC entry 4490 (class 0 OID 0)
-- Dependencies: 277
-- Name: TABLE provenance_activities; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.provenance_activities IS 'PROV-O Activity model representing processing activities';


--
-- TOC entry 4491 (class 0 OID 0)
-- Dependencies: 277
-- Name: COLUMN provenance_activities.prov_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.provenance_activities.prov_id IS 'PROV-O Activity identifier (e.g., activity_embeddings_456)';


--
-- TOC entry 4492 (class 0 OID 0)
-- Dependencies: 277
-- Name: COLUMN provenance_activities.prov_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.provenance_activities.prov_type IS 'PROV-O Activity type (e.g., ont:EmbeddingsProcessing)';


--
-- TOC entry 4493 (class 0 OID 0)
-- Dependencies: 277
-- Name: COLUMN provenance_activities.was_associated_with; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.provenance_activities.was_associated_with IS 'PROV-O wasAssociatedWith agent';


--
-- TOC entry 4494 (class 0 OID 0)
-- Dependencies: 277
-- Name: COLUMN provenance_activities.used_plan; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.provenance_activities.used_plan IS 'PROV-O used plan/protocol';


--
-- TOC entry 276 (class 1259 OID 43689)
-- Name: provenance_activities_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.provenance_activities_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.provenance_activities_id_seq OWNER TO postgres;

--
-- TOC entry 4496 (class 0 OID 0)
-- Dependencies: 276
-- Name: provenance_activities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.provenance_activities_id_seq OWNED BY public.provenance_activities.id;


--
-- TOC entry 244 (class 1259 OID 19645)
-- Name: provenance_chains; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.provenance_chains (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    entity_id uuid,
    entity_type character varying(30) NOT NULL,
    was_derived_from uuid,
    derivation_activity uuid,
    derivation_metadata json,
    created_at timestamp with time zone
);


ALTER TABLE public.provenance_chains OWNER TO ontextract_user;

--
-- TOC entry 275 (class 1259 OID 43676)
-- Name: provenance_entities; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.provenance_entities (
    id integer NOT NULL,
    prov_id character varying(255) NOT NULL,
    prov_type character varying(100) NOT NULL,
    prov_label character varying(500),
    generated_at_time timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    invalidated_at_time timestamp without time zone,
    attributed_to_agent character varying(255),
    derived_from_entity character varying(255),
    generated_by_activity character varying(255),
    document_id integer,
    experiment_id integer,
    version_number integer,
    version_type character varying(50),
    prov_metadata jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.provenance_entities OWNER TO postgres;

--
-- TOC entry 4498 (class 0 OID 0)
-- Dependencies: 275
-- Name: TABLE provenance_entities; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.provenance_entities IS 'PROV-O Entity model representing first-class provenance entities';


--
-- TOC entry 4499 (class 0 OID 0)
-- Dependencies: 275
-- Name: COLUMN provenance_entities.prov_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.provenance_entities.prov_id IS 'PROV-O Entity identifier (e.g., document_123_v2)';


--
-- TOC entry 4500 (class 0 OID 0)
-- Dependencies: 275
-- Name: COLUMN provenance_entities.prov_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.provenance_entities.prov_type IS 'PROV-O Entity type (e.g., ont:Document, ont:ProcessedDocument)';


--
-- TOC entry 4501 (class 0 OID 0)
-- Dependencies: 275
-- Name: COLUMN provenance_entities.derived_from_entity; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.provenance_entities.derived_from_entity IS 'PROV-O wasDerivedFrom relationship';


--
-- TOC entry 4502 (class 0 OID 0)
-- Dependencies: 275
-- Name: COLUMN provenance_entities.generated_by_activity; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.provenance_entities.generated_by_activity IS 'PROV-O wasGeneratedBy relationship';


--
-- TOC entry 274 (class 1259 OID 43675)
-- Name: provenance_entities_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.provenance_entities_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.provenance_entities_id_seq OWNER TO postgres;

--
-- TOC entry 4504 (class 0 OID 0)
-- Dependencies: 274
-- Name: provenance_entities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.provenance_entities_id_seq OWNED BY public.provenance_entities.id;


--
-- TOC entry 248 (class 1259 OID 19817)
-- Name: search_history; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.search_history (
    id integer NOT NULL,
    query text NOT NULL,
    query_type character varying(50),
    results_count integer,
    execution_time double precision,
    user_id character varying(255),
    ip_address character varying(45),
    created_at timestamp without time zone
);


ALTER TABLE public.search_history OWNER TO ontextract_user;

--
-- TOC entry 247 (class 1259 OID 19816)
-- Name: search_history_id_seq; Type: SEQUENCE; Schema: public; Owner: ontextract_user
--

CREATE SEQUENCE public.search_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.search_history_id_seq OWNER TO ontextract_user;

--
-- TOC entry 4506 (class 0 OID 0)
-- Dependencies: 247
-- Name: search_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ontextract_user
--

ALTER SEQUENCE public.search_history_id_seq OWNED BY public.search_history.id;


--
-- TOC entry 242 (class 1259 OID 19593)
-- Name: semantic_drift_activities; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.semantic_drift_activities (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    activity_type character varying(50) NOT NULL,
    start_period character varying(50) NOT NULL,
    end_period character varying(50) NOT NULL,
    temporal_scope_years integer[],
    used_entity uuid,
    generated_entity uuid,
    was_associated_with uuid,
    drift_metrics json,
    detection_algorithm character varying(100),
    algorithm_parameters json,
    started_at_time timestamp with time zone,
    ended_at_time timestamp with time zone,
    activity_status character varying(20),
    drift_detected boolean,
    drift_magnitude numeric(4,3),
    drift_type character varying(30),
    evidence_summary text,
    created_by integer,
    created_at timestamp with time zone,
    CONSTRAINT semantic_drift_activities_activity_status_check CHECK (((activity_status)::text = ANY ((ARRAY['running'::character varying, 'completed'::character varying, 'error'::character varying, 'provisional'::character varying])::text[]))),
    CONSTRAINT semantic_drift_activities_drift_magnitude_check CHECK (((drift_magnitude >= (0)::numeric) AND (drift_magnitude <= (1)::numeric)))
);


ALTER TABLE public.semantic_drift_activities OWNER TO ontextract_user;

--
-- TOC entry 243 (class 1259 OID 19628)
-- Name: term_version_anchors; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.term_version_anchors (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    term_version_id uuid NOT NULL,
    context_anchor_id uuid NOT NULL,
    similarity_score numeric(4,3),
    rank_in_neighborhood integer,
    created_at timestamp with time zone
);


ALTER TABLE public.term_version_anchors OWNER TO ontextract_user;

--
-- TOC entry 239 (class 1259 OID 19524)
-- Name: term_versions; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.term_versions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    term_id uuid NOT NULL,
    temporal_period character varying(50) NOT NULL,
    temporal_start_year integer,
    temporal_end_year integer,
    meaning_description text NOT NULL,
    context_anchor json,
    original_context_anchor json,
    fuzziness_score numeric(4,3),
    confidence_level character varying(10),
    certainty_notes text,
    corpus_source character varying(100),
    source_documents json,
    extraction_method character varying(50),
    generated_at_time timestamp with time zone,
    was_derived_from uuid,
    derivation_type character varying(30),
    version_number integer,
    is_current boolean,
    created_by integer,
    created_at timestamp with time zone,
    neighborhood_overlap numeric(4,3),
    positional_change numeric(4,3),
    similarity_reduction numeric(4,3),
    source_citation text,
    CONSTRAINT term_versions_confidence_level_check CHECK (((confidence_level)::text = ANY ((ARRAY['high'::character varying, 'medium'::character varying, 'low'::character varying])::text[]))),
    CONSTRAINT term_versions_fuzziness_score_check CHECK (((fuzziness_score >= (0)::numeric) AND (fuzziness_score <= (1)::numeric))),
    CONSTRAINT term_versions_neighborhood_overlap_check CHECK (((neighborhood_overlap >= (0)::numeric) AND (neighborhood_overlap <= (1)::numeric))),
    CONSTRAINT term_versions_positional_change_check CHECK (((positional_change >= (0)::numeric) AND (positional_change <= (1)::numeric))),
    CONSTRAINT term_versions_similarity_reduction_check CHECK (((similarity_reduction >= (0)::numeric) AND (similarity_reduction <= (1)::numeric)))
);


ALTER TABLE public.term_versions OWNER TO ontextract_user;

--
-- TOC entry 4507 (class 0 OID 0)
-- Dependencies: 239
-- Name: COLUMN term_versions.source_citation; Type: COMMENT; Schema: public; Owner: ontextract_user
--

COMMENT ON COLUMN public.term_versions.source_citation IS 'Academic citation for this temporal version meaning (e.g., dictionary reference, paper, etc.)';


--
-- TOC entry 237 (class 1259 OID 19487)
-- Name: terms; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.terms (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    term_text character varying(255) NOT NULL,
    entry_date timestamp with time zone,
    status character varying(20) NOT NULL,
    created_by integer,
    updated_by integer,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    description text,
    etymology text,
    notes text,
    research_domain character varying(100),
    selection_rationale text,
    historical_significance text,
    CONSTRAINT terms_status_check CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'provisional'::character varying, 'deprecated'::character varying])::text[])))
);


ALTER TABLE public.terms OWNER TO ontextract_user;

--
-- TOC entry 234 (class 1259 OID 17862)
-- Name: text_segments_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.text_segments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.text_segments_id_seq OWNER TO postgres;

--
-- TOC entry 4508 (class 0 OID 0)
-- Dependencies: 234
-- Name: text_segments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.text_segments_id_seq OWNED BY public.text_segments.id;


--
-- TOC entry 262 (class 1259 OID 43281)
-- Name: tool_execution_logs; Type: TABLE; Schema: public; Owner: ontextract_user
--

CREATE TABLE public.tool_execution_logs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    orchestration_decision_id uuid NOT NULL,
    tool_name character varying(50) NOT NULL,
    tool_version character varying(50),
    execution_order integer,
    started_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    completed_at timestamp with time zone,
    execution_time_ms integer,
    execution_status character varying(20) DEFAULT 'running'::character varying,
    output_data jsonb,
    error_message text,
    memory_usage_mb integer,
    cpu_usage_percent numeric(5,2),
    output_quality_score numeric(4,3),
    CONSTRAINT tool_execution_logs_output_quality_score_check CHECK (((output_quality_score >= (0)::numeric) AND (output_quality_score <= (1)::numeric))),
    CONSTRAINT tool_execution_logs_status_check CHECK (((execution_status)::text = ANY ((ARRAY['running'::character varying, 'completed'::character varying, 'error'::character varying, 'timeout'::character varying, 'skipped'::character varying])::text[])))
);


ALTER TABLE public.tool_execution_logs OWNER TO ontextract_user;

--
-- TOC entry 4510 (class 0 OID 0)
-- Dependencies: 262
-- Name: TABLE tool_execution_logs; Type: COMMENT; Schema: public; Owner: ontextract_user
--

COMMENT ON TABLE public.tool_execution_logs IS 'Detailed logs of individual NLP tool execution with performance metrics';


--
-- TOC entry 4511 (class 0 OID 0)
-- Dependencies: 262
-- Name: COLUMN tool_execution_logs.execution_order; Type: COMMENT; Schema: public; Owner: ontextract_user
--

COMMENT ON COLUMN public.tool_execution_logs.execution_order IS 'Order in processing pipeline (0 = first, higher = later)';


--
-- TOC entry 4512 (class 0 OID 0)
-- Dependencies: 262
-- Name: COLUMN tool_execution_logs.output_quality_score; Type: COMMENT; Schema: public; Owner: ontextract_user
--

COMMENT ON COLUMN public.tool_execution_logs.output_quality_score IS 'Quality assessment of tool output (0.0 = poor, 1.0 = excellent)';


--
-- TOC entry 235 (class 1259 OID 17863)
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    username character varying(80) NOT NULL,
    email character varying(120) NOT NULL,
    password_hash character varying(256) NOT NULL,
    first_name character varying(50),
    last_name character varying(50),
    organization character varying(100),
    is_active boolean NOT NULL,
    is_admin boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone,
    last_login timestamp without time zone
);


ALTER TABLE public.users OWNER TO postgres;

--
-- TOC entry 236 (class 1259 OID 17868)
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO postgres;

--
-- TOC entry 4514 (class 0 OID 0)
-- Dependencies: 236
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- TOC entry 280 (class 1259 OID 49181)
-- Name: version_changelog_id_seq; Type: SEQUENCE; Schema: public; Owner: ontextract_user
--

CREATE SEQUENCE public.version_changelog_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.version_changelog_id_seq OWNER TO ontextract_user;

--
-- TOC entry 4516 (class 0 OID 0)
-- Dependencies: 280
-- Name: version_changelog_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ontextract_user
--

ALTER SEQUENCE public.version_changelog_id_seq OWNED BY public.version_changelog.id;


--
-- TOC entry 3812 (class 2604 OID 43143)
-- Name: document_embeddings id; Type: DEFAULT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.document_embeddings ALTER COLUMN id SET DEFAULT nextval('public.document_embeddings_id_seq'::regclass);


--
-- TOC entry 3863 (class 2604 OID 43775)
-- Name: document_processing_summary id; Type: DEFAULT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.document_processing_summary ALTER COLUMN id SET DEFAULT nextval('public.document_processing_summary_id_seq'::regclass);


--
-- TOC entry 3785 (class 2604 OID 17869)
-- Name: documents id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.documents ALTER COLUMN id SET DEFAULT nextval('public.documents_id_seq'::regclass);


--
-- TOC entry 3807 (class 2604 OID 19805)
-- Name: domains id; Type: DEFAULT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.domains ALTER COLUMN id SET DEFAULT nextval('public.domains_id_seq'::regclass);


--
-- TOC entry 3838 (class 2604 OID 43416)
-- Name: experiment_documents_v2 id; Type: DEFAULT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.experiment_documents_v2 ALTER COLUMN id SET DEFAULT nextval('public.experiment_documents_v2_id_seq'::regclass);


--
-- TOC entry 3793 (class 2604 OID 17870)
-- Name: experiments id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.experiments ALTER COLUMN id SET DEFAULT nextval('public.experiments_id_seq'::regclass);


--
-- TOC entry 3794 (class 2604 OID 17871)
-- Name: extracted_entities id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.extracted_entities ALTER COLUMN id SET DEFAULT nextval('public.extracted_entities_id_seq'::regclass);


--
-- TOC entry 3809 (class 2604 OID 19829)
-- Name: ontologies id; Type: DEFAULT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.ontologies ALTER COLUMN id SET DEFAULT nextval('public.ontologies_id_seq'::regclass);


--
-- TOC entry 3811 (class 2604 OID 19866)
-- Name: ontology_entities id; Type: DEFAULT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.ontology_entities ALTER COLUMN id SET DEFAULT nextval('public.ontology_entities_id_seq'::regclass);


--
-- TOC entry 3795 (class 2604 OID 17872)
-- Name: ontology_mappings id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ontology_mappings ALTER COLUMN id SET DEFAULT nextval('public.ontology_mappings_id_seq'::regclass);


--
-- TOC entry 3810 (class 2604 OID 19850)
-- Name: ontology_versions id; Type: DEFAULT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.ontology_versions ALTER COLUMN id SET DEFAULT nextval('public.ontology_versions_id_seq'::regclass);


--
-- TOC entry 3796 (class 2604 OID 17873)
-- Name: processing_jobs id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.processing_jobs ALTER COLUMN id SET DEFAULT nextval('public.processing_jobs_id_seq'::regclass);


--
-- TOC entry 3859 (class 2604 OID 43693)
-- Name: provenance_activities id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.provenance_activities ALTER COLUMN id SET DEFAULT nextval('public.provenance_activities_id_seq'::regclass);


--
-- TOC entry 3855 (class 2604 OID 43679)
-- Name: provenance_entities id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.provenance_entities ALTER COLUMN id SET DEFAULT nextval('public.provenance_entities_id_seq'::regclass);


--
-- TOC entry 3808 (class 2604 OID 19820)
-- Name: search_history id; Type: DEFAULT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.search_history ALTER COLUMN id SET DEFAULT nextval('public.search_history_id_seq'::regclass);


--
-- TOC entry 3797 (class 2604 OID 17874)
-- Name: text_segments id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.text_segments ALTER COLUMN id SET DEFAULT nextval('public.text_segments_id_seq'::regclass);


--
-- TOC entry 3798 (class 2604 OID 17875)
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- TOC entry 3867 (class 2604 OID 49185)
-- Name: version_changelog id; Type: DEFAULT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.version_changelog ALTER COLUMN id SET DEFAULT nextval('public.version_changelog_id_seq'::regclass);


--
-- TOC entry 4381 (class 0 OID 19509)
-- Dependencies: 238
-- Data for Name: analysis_agents; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.analysis_agents (id, agent_type, name, description, version, algorithm_type, model_parameters, training_data, expertise_domain, institutional_affiliation, created_at, is_active, user_id) FROM stdin;
4a32b8b0-8581-4975-8785-929ec8c4878f	Person	Manual Curation	Human curator performing manual semantic analysis	1.0	Manual_Curation	\N	\N	\N	\N	\N	\N	\N
f959c050-3cc8-4549-a2f2-d3894198ca53	SoftwareAgent	HistBERT Temporal Embedding Alignment	Historical BERT model for temporal semantic alignment	1.0	HistBERT	\N	\N	\N	\N	\N	\N	\N
fdacd5b5-4b12-41fe-83d2-172a5581e53e	SoftwareAgent	Word2Vec Diachronic Analysis	Word2Vec model trained on temporal corpora	1.0	Word2Vec	\N	\N	\N	\N	\N	\N	\N
89c10255-275f-40ac-9139-8b3fbb9c2026	SoftwareAgent	demo_orchestrator	Demo LLM orchestration agent	1.0.0	llm_orchestration	{"method": "llm_orchestration", "models": ["claude-sonnet-4", "gpt-4", "gemini-1.5"]}	\N	\N	\N	2025-09-06 16:00:24.194906-04	t	\N
\.


--
-- TOC entry 4384 (class 0 OID 19576)
-- Dependencies: 241
-- Data for Name: context_anchors; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.context_anchors (id, anchor_term, frequency, first_used_in, last_used_in, created_at) FROM stdin;
a50cc9e3-f468-4a60-9278-14fc783189e5	agent	1	\N	\N	2025-08-24 13:18:57.911853-04
466fe463-f97c-40c8-b13f-63c539b619d8	cell	1	\N	\N	2025-08-24 13:26:19.747627-04
0f6ed02a-0d5d-4325-91cf-7f8701b4f480	ontology	1	\N	\N	2025-08-24 13:27:14.07582-04
187a15c2-0041-4dc1-a4fe-c6d5efc265e9	granularity	1	\N	\N	2025-08-24 13:37:42.66053-04
4e4d398a-e465-4d5a-a743-903ef78bf7d5	consisting	1	\N	\N	2025-08-24 13:37:42.669698-04
bbe2884b-d4b2-44ef-a40f-5bf2bc95d6af	appearing	1	\N	\N	2025-08-24 13:37:42.67267-04
c794432d-7542-45c4-9eb3-56f383f0a232	consist	1	\N	\N	2025-08-24 13:37:42.675239-04
20bbf849-cb9f-4bd1-b242-68da857075e3	finely	1	\N	\N	2025-08-24 13:37:42.677822-04
be420c20-5278-4184-a725-3df467434af4	detailed	1	\N	\N	2025-08-24 13:37:42.680428-04
ded8a9b4-6329-4289-8481-f3d3a580821b	word	1	\N	\N	2025-09-02 14:12:42.815052-04
e75826c3-2f6a-447e-b584-70fd0278bea9	language unit	1	\N	\N	2025-09-02 14:12:42.82656-04
acc4e4ad-04fc-42b6-9f37-b70e132b26f4	charade	1	\N	\N	2025-09-02 14:12:42.829576-04
14c18a05-b195-46a3-a5b0-bc3381db0894	meronym	1	\N	\N	2025-09-02 14:12:42.832622-04
e52c0e9a-c7b1-43c1-9db8-1e2be5f7af1a	hooligan	1	\N	\N	2025-08-24 14:03:22.104634-04
99267944-387f-4c8d-a0ba-62bbc69d2f4d	usually	1	\N	\N	2025-08-24 14:03:22.110767-04
0bd2bb6f-36f3-46cf-9b60-d7ab53b77fa5	young	1	\N	\N	2025-08-24 14:03:22.113901-04
03406a50-523c-43c3-aeb4-e151c60f442a	engages	1	\N	\N	2025-08-24 14:03:22.118188-04
\.


--
-- TOC entry 4399 (class 0 OID 43140)
-- Dependencies: 256
-- Data for Name: document_embeddings; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.document_embeddings (id, document_id, term, period, embedding, model_name, context_window, extraction_method, metadata, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4421 (class 0 OID 43772)
-- Dependencies: 279
-- Data for Name: document_processing_summary; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.document_processing_summary (id, document_id, processing_type, status, source_document_id, job_id, priority, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4364 (class 0 OID 17819)
-- Dependencies: 221
-- Data for Name: documents; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.documents (id, title, content_type, document_type, reference_subtype, file_type, original_filename, file_path, file_size, source_metadata, content, content_preview, detected_language, language_confidence, status, word_count, character_count, created_at, updated_at, processed_at, user_id, embedding, parent_document_id, processing_metadata, version_number, version_type, experiment_id, source_document_id, processing_notes) FROM stdin;
116	Ground semantic (v3)	text	document	\N	\N	\N	\N	\N	\N	Ground semantic evolution in foundational scholarly works across disciplines, using peer-reviewed literature rather than corpus statistics alone for authoritative meaning fixation.	Ground semantic evolution in foundational scholarly works across disciplines, using peer-reviewed literature rather than corpus statistics alone for authoritative meaning fixation.	en	0.9	active	21	180	2025-09-07 23:50:49.996566	2025-09-07 23:50:49.996569	\N	1	\N	\N	{"segmentation_method": "paragraph", "chunk_size": 500, "overlap": 50, "experiment_id": null, "processing_notes": "Document segmentation using paragraph method"}	3	processed	\N	114	\N
112	Test	text	document	\N	\N	\N	\N	\N	\N	This is a clean test document for verifying inheritance-based versioning and automatic redirect functionality. It contains enough content to be processed for both embeddings and segmentation.	This is a clean test document for verifying inheritance-based versioning and automatic redirect functionality. It contains enough content to be processed for both embeddings and segmentation.	en	0.9	uploaded	26	191	2025-09-07 22:11:55.770284	2025-09-07 22:11:55.770287	\N	1	\N	\N	\N	1	original	\N	\N	\N
113	Test (v2)	text	document	\N	\N	\N	\N	\N	\N	This is a clean test document for verifying inheritance-based versioning and automatic redirect functionality. It contains enough content to be processed for both embeddings and segmentation.	This is a clean test document for verifying inheritance-based versioning and automatic redirect functionality. It contains enough content to be processed for both embeddings and segmentation.	en	0.9	active	26	191	2025-09-07 22:11:57.04926	2025-09-07 22:11:57.049263	\N	1	\N	\N	{"embedding_method": "local", "experiment_id": null, "processing_notes": "Embeddings processing using local method"}	2	processed	\N	112	\N
114	Ground semantic	text	document	\N	\N	\N	\N	\N	\N	Ground semantic evolution in foundational scholarly works across disciplines, using peer-reviewed literature rather than corpus statistics alone for authoritative meaning fixation.	Ground semantic evolution in foundational scholarly works across disciplines, using peer-reviewed literature rather than corpus statistics alone for authoritative meaning fixation.	en	0.9	uploaded	21	180	2025-09-07 22:18:37.197004	2025-09-07 22:18:37.197007	\N	1	\N	\N	\N	1	original	\N	\N	\N
115	Ground semantic (v2)	text	document	\N	\N	\N	\N	\N	\N	Ground semantic evolution in foundational scholarly works across disciplines, using peer-reviewed literature rather than corpus statistics alone for authoritative meaning fixation.	Ground semantic evolution in foundational scholarly works across disciplines, using peer-reviewed literature rather than corpus statistics alone for authoritative meaning fixation.	en	0.9	active	21	180	2025-09-07 22:18:42.477585	2025-09-07 22:18:42.477587	\N	1	\N	\N	{"embedding_method": "local", "experiment_id": null, "processing_notes": "Embeddings processing using local method"}	2	processed	\N	114	\N
\.


--
-- TOC entry 4389 (class 0 OID 19802)
-- Dependencies: 246
-- Data for Name: domains; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.domains (id, uuid, name, display_name, namespace_uri, description, metadata, is_active, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4366 (class 0 OID 17825)
-- Dependencies: 223
-- Data for Name: experiment_documents; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.experiment_documents (experiment_id, document_id, added_at, processing_status, processing_metadata, embeddings_applied, embeddings_metadata, segments_created, segments_metadata, nlp_analysis_completed, nlp_results, processed_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4411 (class 0 OID 43413)
-- Dependencies: 268
-- Data for Name: experiment_documents_v2; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.experiment_documents_v2 (id, experiment_id, document_id, processing_status, embedding_model, embedding_dimension, embeddings_applied, embedding_metadata, segmentation_method, segment_size, segments_created, segmentation_metadata, nlp_analysis_completed, nlp_tools_used, processing_started_at, processing_completed_at, embeddings_generated_at, segmentation_completed_at, added_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4367 (class 0 OID 17828)
-- Dependencies: 224
-- Data for Name: experiment_references; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.experiment_references (experiment_id, reference_id, include_in_analysis, added_at, notes) FROM stdin;
\.


--
-- TOC entry 4368 (class 0 OID 17833)
-- Dependencies: 225
-- Data for Name: experiments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.experiments (id, name, description, experiment_type, configuration, status, results, results_summary, created_at, updated_at, started_at, completed_at, user_id) FROM stdin;
\.


--
-- TOC entry 4370 (class 0 OID 17839)
-- Dependencies: 227
-- Data for Name: extracted_entities; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.extracted_entities (id, entity_text, entity_type, entity_subtype, context_before, context_after, sentence, start_position, end_position, paragraph_number, sentence_number, confidence_score, extraction_method, properties, language, normalized_form, created_at, updated_at, processing_job_id, text_segment_id) FROM stdin;
\.


--
-- TOC entry 4383 (class 0 OID 19557)
-- Dependencies: 240
-- Data for Name: fuzziness_adjustments; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.fuzziness_adjustments (id, term_version_id, original_score, adjusted_score, adjustment_reason, adjusted_by, created_at) FROM stdin;
\.


--
-- TOC entry 4408 (class 0 OID 43347)
-- Dependencies: 265
-- Data for Name: learning_patterns; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.learning_patterns (id, pattern_name, pattern_type, context_signature, conditions, recommendations, confidence, derived_from_feedback, researcher_authority, times_applied, success_rate, last_applied, pattern_status, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4406 (class 0 OID 43301)
-- Dependencies: 263
-- Data for Name: multi_model_consensus; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.multi_model_consensus (id, orchestration_decision_id, validation_type, models_involved, consensus_method, model_responses, model_confidence_scores, model_agreement_matrix, consensus_reached, consensus_confidence, final_decision, disagreement_areas, started_at, completed_at, total_processing_time_ms) FROM stdin;
\.


--
-- TOC entry 4401 (class 0 OID 43172)
-- Dependencies: 258
-- Data for Name: oed_definitions; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.oed_definitions (id, term_id, definition_number, first_cited_year, last_cited_year, part_of_speech, domain_label, status, quotation_count, sense_frequency_rank, historical_period, period_start_year, period_end_year, generated_at_time, was_attributed_to, was_derived_from, derivation_type, definition_confidence, created_at, updated_at, definition_excerpt, oed_sense_id, oed_url) FROM stdin;
a9f09ecd-95ae-4a81-a40c-868c83dd3442	d36546b4-c1d1-4faa-aa7a-aec75e906917	1.a.	1382	1850	noun	\N	historical	0	\N	\N	\N	\N	2025-09-06 13:48:59.950804-04	OED_API_Service	\N	definition_extraction	high	2025-09-06 13:48:59.953316-04	2025-09-06 13:48:59.953317-04	A person who or thing which acts upon someone or something; one who or that which exerts power; the doer of an action. Sometimes contrasted with the patient (instrument, etc.) undergoing the action. Cf. actorn. 3a. Earliest in Alchemy: a force capable of acting upon matter, an active principle. Now 	\N	https://www.oed.com/dictionary/agent_n
104991d8-00bb-4dab-8d07-f31e4a39c9df	d36546b4-c1d1-4faa-aa7a-aec75e906917	1.b.	1471	2010	noun	\N	current	0	\N	\N	\N	\N	2025-09-06 13:48:59.950937-04	OED_API_Service	\N	definition_extraction	high	2025-09-06 13:48:59.953318-04	2025-09-06 13:48:59.953319-04	A person or thing that operates in a particular direction, or produces a specied effect; the cause of some process or change. Frequently with for, in, of. Sometimes dicult to distinguish from the means or agency by which an eect is produced: cf. sense A.3.a1500– The fyrst [kind of combining] is call	\N	https://www.oed.com/dictionary/agent_n
f02d7b42-a522-43e5-ba10-41709e79e170	d36546b4-c1d1-4faa-aa7a-aec75e906917	1.c.	1592	2010	noun	\N	current	0	\N	\N	\N	\N	2025-09-06 13:48:59.951024-04	OED_API_Service	\N	definition_extraction	high	2025-09-06 13:48:59.95332-04	2025-09-06 13:48:59.95332-04	Grammar. The doer of an action, typically expressed as the subject of an active verb or in a by-phrase with a passive verb. Cf. agent nounn.Faieth is produced and brought foorth by the grace of God, as chiefe agent and worker thereof. W. Fulke, Confut. Popishe Libelle (new edition) f. 108 I stepped 	\N	https://www.oed.com/dictionary/agent_n
fa8b4941-5348-459b-ad15-90584a8daf3c	d36546b4-c1d1-4faa-aa7a-aec75e906917	1.d.	1592	\N	noun	\N	current	0	\N	\N	\N	\N	2025-09-06 13:48:59.951066-04	OED_API_Service	\N	definition_extraction	high	2025-09-06 13:48:59.953321-04	2025-09-06 13:48:59.953321-04	Parapsychology. In telepathy: the person who originates an impression (opposed to the percipient who receives it). parapsychology	\N	https://www.oed.com/dictionary/agent_n
28709915-9f35-4d1f-864c-6176ccee555b	d36546b4-c1d1-4faa-aa7a-aec75e906917	2.	1651	\N	noun	\N	current	0	\N	\N	\N	\N	2025-09-06 13:48:59.951105-04	OED_API_Service	\N	definition_extraction	high	2025-09-06 13:48:59.953322-04	2025-09-06 13:48:59.953322-04	A person acting on behalf of another.	\N	https://www.oed.com/dictionary/agent_n
5d1d3165-05aa-4761-9dd3-a2cafdb74363	d36546b4-c1d1-4faa-aa7a-aec75e906917	2.a.	1523	2007	noun	\N	current	0	\N	\N	\N	\N	2025-09-06 13:48:59.951182-04	OED_API_Service	\N	definition_extraction	high	2025-09-06 13:48:59.953323-04	2025-09-06 13:48:59.953323-04	A person who acts as a substitute for another; one who undertakes negotiations or transactions on behalf of a superior, employer, or principal; a deputy, steward, representative; (in early use) an ambassador, emissary. Also gurative. Now chiey in legal contexts. In Scots Law: a solicitor, advocate (	\N	https://www.oed.com/dictionary/agent_n
81bb0160-4ba5-4ca9-9415-7864d7b7e6cb	d36546b4-c1d1-4faa-aa7a-aec75e906917	2.b.	1548	2000	noun	\N	current	0	\N	\N	\N	\N	2025-09-06 13:48:59.951266-04	OED_API_Service	\N	definition_extraction	high	2025-09-06 13:48:59.953323-04	2025-09-06 13:48:59.953324-04	In commercial use: a person or company that provides a particular service, typically one that involves arranging transactions between two other parties; (also) a person or company that represents an organization, esp. in a particular region; a business or sales representative. Cf. agencyn. I.1b.We h	\N	https://www.oed.com/dictionary/agent_n
09ae3af2-6298-4d78-bd41-676783c1ab48	d36546b4-c1d1-4faa-aa7a-aec75e906917	2.c.	1707	2007	noun	\N	current	0	\N	\N	\N	\N	2025-09-06 13:48:59.951337-04	OED_API_Service	\N	definition_extraction	high	2025-09-06 13:48:59.953324-04	2025-09-06 13:48:59.953325-04	In colonial North America and subsequently the United States: an ofcial appointed to represent the government in dealing with an Indigenous people; = Indian agentn. Now historical.Most Bills of Exchange are ordinarily Negotiated by the..Interposition of a certain Set of Men commonly called Agents, o	\N	https://www.oed.com/dictionary/agent_n
66edd4c0-f212-478d-aee8-20da3942e970	d36546b4-c1d1-4faa-aa7a-aec75e906917	2.d.	1850	\N	noun	\N	current	0	\N	\N	\N	\N	2025-09-06 13:48:59.951375-04	OED_API_Service	\N	definition_extraction	high	2025-09-06 13:48:59.953325-04	2025-09-06 13:48:59.953326-04	A person who works secretly to obtain information for a government or other ofcial body; a spy. double, secret, treble agent, etc.: see the rst element. espionage	\N	https://www.oed.com/dictionary/agent_n
49a6d8d3-fb99-4b91-8588-af192d0542fc	d36546b4-c1d1-4faa-aa7a-aec75e906917	2.e.	1804	2008	noun	\N	current	0	\N	\N	\N	\N	2025-09-06 13:48:59.951442-04	OED_API_Service	\N	definition_extraction	high	2025-09-06 13:48:59.953326-04	2025-09-06 13:48:59.953327-04	A person who negotiates and manages business, nancial, publicity, or contractual matters for an actor, performer, writer, etc. In earliest use: a theatrical agent. literary, press, publicity, sports agent, etc.: see the rst element.There can be but one head to an Indian agency, and the agent should 	\N	https://www.oed.com/dictionary/agent_n
125cfe94-605a-4745-81e0-8154bbae8907	d36546b4-c1d1-4faa-aa7a-aec75e906917	2.f.	\N	\N	noun	\N	current	0	\N	\N	\N	\N	2025-09-06 13:48:59.951477-04	OED_API_Service	\N	definition_extraction	high	2025-09-06 13:48:59.953327-04	2025-09-06 13:48:59.953327-04	U.S. A stagecoach robber; = road agentn. Now historical. U.S. Englishhistorical	\N	https://www.oed.com/dictionary/agent_n
6d870cae-fe0a-4acb-8ada-9747ffd3ad79	d36546b4-c1d1-4faa-aa7a-aec75e906917	3.	1579	2003	noun	\N	current	0	\N	\N	\N	\N	2025-09-06 13:48:59.951551-04	OED_API_Service	\N	definition_extraction	high	2025-09-06 13:48:59.953328-04	2025-09-06 13:48:59.953328-04	The means by which something is done; the material cause or instrument through which an effect is produced (often implying a rational employer or contriver).Mr. Schemer, the agent, had no situation for our hero upon his books, but Proteus heard..that Mr. Make-a-bill..was in great want of a person at	\N	https://www.oed.com/dictionary/agent_n
917e390a-36d4-4c06-bf2e-a28669b05e2a	d36546b4-c1d1-4faa-aa7a-aec75e906917	4.	1593	2002	noun	\N	current	0	\N	\N	\N	\N	2025-09-06 13:48:59.951624-04	OED_API_Service	\N	definition_extraction	high	2025-09-06 13:48:59.953329-04	2025-09-06 13:48:59.953329-04	Chemistry. A substance that brings about a chemical or physical effect or causes a chemical reaction. In later use chiey with preceding modifying word specifying the nature of the effect or reaction. Cf. reagentn. 2. alkylating, oxidizing, reducing, wetting agent, etc.: see the rst element.The gallo	\N	https://www.oed.com/dictionary/agent_n
52840f35-2cd6-47d9-80ab-0f97f59fb24c	d36546b4-c1d1-4faa-aa7a-aec75e906917	5.	1500	2023	noun	\N	current	0	\N	\N	\N	\N	2025-09-06 13:48:59.951776-04	OED_API_Service	\N	definition_extraction	high	2025-09-06 13:48:59.95333-04	2025-09-06 13:48:59.95333-04	Computing. A program that (autonomously) performs a task such as information retrieval or processing on behalf of a client or user. More fully software agent, user agent. computing ADJECTIVE Acting, exerting power (sometimes contrasted with patientadj. A.2a). † party agentnounObsoleteLaw the person 	\N	https://www.oed.com/dictionary/agent_n
82846436-822b-4ce2-b0b3-c87e7c6e2d9a	d36546b4-c1d1-4faa-aa7a-aec75e906917	15	1656	1840	noun	\N	historical	0	\N	\N	\N	\N	2025-09-06 13:48:59.951898-04	OED_API_Service	\N	definition_extraction	high	2025-09-06 13:48:59.953331-04	2025-09-06 13:48:59.953331-04	a. A person able to act freely, as by the exercise of free will, or because of the absence of restriction, constraint, or responsibilities; b. Sport… reagent, n.1656– Chemistry. A substance used in testing for other substances, or for reacting with them in a particular way; (more widely) any substan	\N	https://www.oed.com/dictionary/agent_n
bbe4b47d-678f-4dd2-a554-9f12a0ddaab1	d36546b4-c1d1-4faa-aa7a-aec75e906917	16	1843	1849	noun	\N	historical	0	\N	\N	\N	\N	2025-09-06 13:48:59.951954-04	OED_API_Service	\N	definition_extraction	high	2025-09-06 13:48:59.953332-04	2025-09-06 13:48:59.953332-04	a. Chiey U.S. a person in charge of a railway or (formerly) stagecoach station; b. a person who works for (a particular branch of) an intelligence… ning agent, n.1843– A substance used to clarify a liquid; spec. (a) a substance used to remove organic compounds from a liquid, esp. beer or wine, to im	\N	https://www.oed.com/dictionary/agent_n
d366b629-0683-4612-89f7-3c62a643fcb4	d36546b4-c1d1-4faa-aa7a-aec75e906917	17	1852	1883	noun	\N	historical	0	\N	\N	\N	\N	2025-09-06 13:48:59.952006-04	OED_API_Service	\N	definition_extraction	high	2025-09-06 13:48:59.953333-04	2025-09-06 13:48:59.953333-04	a. A person who or a business which arranges transport or travel for goods or passengers, or sells tickets in advance for concerts, plays, or other… Frequently derogatory in early use, denoting agents for railway or shipping companies who issued tickets or passes which were greatly overpriced or inv	\N	https://www.oed.com/dictionary/agent_n
43187b5b-3250-421b-a517-85a138043054	d36546b4-c1d1-4faa-aa7a-aec75e906917	18	1884	1910	noun	\N	historical	0	\N	\N	\N	\N	2025-09-06 13:48:59.952063-04	OED_API_Service	\N	definition_extraction	high	2025-09-06 13:48:59.953333-04	2025-09-06 13:48:59.953334-04	a. Any substance added to beer or other alcohol to give it a bitter avour; cf. bittering, n.² 2; b. a substance added to a (typically toxic)… tourist agent, n.1884– raising agent, n.1885–Oxford University Press uses cookies to enhance your experience on our website. By selecting ‘accept all’ you are	\N	https://www.oed.com/dictionary/agent_n
d75de39e-2c6b-4452-897c-46b25c6424f5	d36546b4-c1d1-4faa-aa7a-aec75e906917	19	1915	2024	noun	\N	current	0	\N	\N	\N	\N	2025-09-06 13:48:59.952154-04	OED_API_Service	\N	definition_extraction	high	2025-09-06 13:48:59.953334-04	2025-09-06 13:48:59.953335-04	a. An agent authorized to inspect, survey, and purchase land for development (rare); b. (in the construction industry) a person responsible for… marketing agent, n.1915– harassing agent, n.1919– A non-lethal chemical which is deployed in the form of a gas or aerosol and used to incapacitate an enemy	\N	https://www.oed.com/dictionary/agent_n
\.


--
-- TOC entry 4400 (class 0 OID 43159)
-- Dependencies: 257
-- Data for Name: oed_etymology; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.oed_etymology (id, term_id, etymology_text, origin_language, first_recorded_year, etymology_confidence, language_family, root_analysis, morphology, generated_at_time, was_attributed_to, was_derived_from, derivation_type, source_version, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4402 (class 0 OID 43188)
-- Dependencies: 259
-- Data for Name: oed_historical_stats; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.oed_historical_stats (id, term_id, time_period, start_year, end_year, definition_count, sense_count, quotation_span_years, earliest_quotation_year, latest_quotation_year, semantic_stability_score, domain_shift_indicator, part_of_speech_changes, started_at_time, ended_at_time, was_associated_with, used_entity, generated_entity, oed_edition, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4403 (class 0 OID 43204)
-- Dependencies: 260
-- Data for Name: oed_quotation_summaries; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.oed_quotation_summaries (id, term_id, oed_definition_id, quotation_year, author_name, work_title, domain_context, usage_type, has_technical_usage, represents_semantic_shift, chronological_rank, generated_at_time, was_attributed_to, was_derived_from, derivation_type, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4393 (class 0 OID 19826)
-- Dependencies: 250
-- Data for Name: ontologies; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.ontologies (id, uuid, domain_id, name, base_uri, description, is_base, is_editable, parent_ontology_id, ontology_type, metadata, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4397 (class 0 OID 19863)
-- Dependencies: 254
-- Data for Name: ontology_entities; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.ontology_entities (id, ontology_id, entity_type, uri, label, comment, parent_uri, domain, range, properties, embedding, created_at) FROM stdin;
\.


--
-- TOC entry 4372 (class 0 OID 17845)
-- Dependencies: 229
-- Data for Name: ontology_mappings; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.ontology_mappings (id, ontology_uri, concept_label, concept_definition, parent_concepts, child_concepts, related_concepts, mapping_confidence, mapping_method, mapping_source, semantic_type, domain, properties, is_verified, verified_by, verification_notes, alternative_mappings, created_at, updated_at, verified_at, extracted_entity_id) FROM stdin;
\.


--
-- TOC entry 4395 (class 0 OID 19847)
-- Dependencies: 252
-- Data for Name: ontology_versions; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.ontology_versions (id, ontology_id, version_number, version_tag, content, content_hash, change_summary, created_by, created_at, is_current, is_draft, workflow_status, metadata) FROM stdin;
\.


--
-- TOC entry 4404 (class 0 OID 43237)
-- Dependencies: 261
-- Data for Name: orchestration_decisions; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.orchestration_decisions (id, activity_type, started_at_time, ended_at_time, activity_status, document_id, experiment_id, term_text, input_metadata, document_characteristics, orchestrator_provider, orchestrator_model, orchestrator_prompt, orchestrator_response, orchestrator_response_time_ms, selected_tools, embedding_model, processing_strategy, expected_runtime_seconds, decision_confidence, reasoning_summary, decision_factors, decision_validated, actual_runtime_seconds, tool_execution_success, was_associated_with, used_entity, created_at, created_by) FROM stdin;
\.


--
-- TOC entry 4407 (class 0 OID 43319)
-- Dependencies: 264
-- Data for Name: orchestration_feedback; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.orchestration_feedback (id, orchestration_decision_id, researcher_id, researcher_expertise, feedback_type, feedback_scope, original_decision, researcher_preference, agreement_level, confidence_assessment, reasoning, domain_specific_factors, suggested_tools, suggested_embedding_model, suggested_processing_strategy, alternative_reasoning, feedback_status, integration_notes, subsequent_decisions_influenced, improvement_verified, verification_notes, provided_at, reviewed_at, integrated_at) FROM stdin;
\.


--
-- TOC entry 4409 (class 0 OID 43371)
-- Dependencies: 266
-- Data for Name: orchestration_overrides; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.orchestration_overrides (id, orchestration_decision_id, researcher_id, override_type, original_decision, overridden_decision, justification, expert_knowledge_applied, override_applied, execution_results, performance_comparison, applied_at) FROM stdin;
\.


--
-- TOC entry 4374 (class 0 OID 17851)
-- Dependencies: 231
-- Data for Name: processing_jobs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.processing_jobs (id, job_type, job_name, provider, model, parameters, status, progress_percent, current_step, total_steps, result_data, result_summary, error_message, error_details, retry_count, max_retries, tokens_used, processing_time, cost_estimate, created_at, started_at, completed_at, updated_at, user_id, document_id, parent_job_id) FROM stdin;
28	generate_embeddings	\N	\N	\N	{"embedding_method": "local", "original_document_id": 114, "version_type": "processed", "prov_entity_id": "document_115_v2", "prov_activity_id": "activity_embeddings_115"}	completed	0	\N	\N	{"embedding_method": "local", "embedding_dimensions": 1536, "chunk_count": 1, "processing_time": 0.8251810073852539, "model_used": "openai:text-embedding-ada-002", "total_embeddings": 1, "content_length": 180}	\N	\N	\N	0	3	\N	0.8251810073852539	\N	2025-09-07 22:18:42.490425	\N	\N	2025-09-07 22:18:43.554434	1	115	\N
29	segment_document	\N	\N	\N	{"method": "paragraph", "chunk_size": 500, "overlap": 50, "original_document_id": 115, "version_type": "processed", "prov_entity_id": "document_116_v3", "prov_activity_id": "activity_segmentation_116"}	completed	0	\N	\N	{"segment_count": 1, "chunk_size": 500, "overlap": 50, "total_words": 21}	\N	\N	\N	0	3	\N	\N	\N	2025-09-07 23:50:50.021673	\N	\N	2025-09-07 23:50:50.215925	1	116	\N
27	generate_embeddings	\N	\N	\N	{"embedding_method": "local", "original_document_id": 112, "version_type": "processed", "prov_entity_id": "document_113_v2", "prov_activity_id": "activity_embeddings_113"}	completed	0	\N	\N	{"embedding_method": "local", "embedding_dimensions": 1536, "chunk_count": 1, "processing_time": 0.42891645431518555, "model_used": "openai:text-embedding-ada-002", "total_embeddings": 1, "content_length": 191}	\N	\N	\N	0	3	\N	0.42891645431518555	\N	2025-09-07 22:11:57.056728	\N	\N	2025-09-07 22:11:57.672566	1	113	\N
\.


--
-- TOC entry 4413 (class 0 OID 43560)
-- Dependencies: 270
-- Data for Name: prov_activities; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.prov_activities (activity_id, activity_type, startedattime, endedattime, wasassociatedwith, activity_parameters, activity_status, activity_metadata, created_at) FROM stdin;
cbb11d95-287b-4235-b423-9d3d152e1562	langextract_document_analysis	2025-09-07 07:19:25.920962-04	\N	ed8306b9-db79-4e8a-b912-4abc776661a9	{"document_id": 70, "text_length": 112006, "gemini_model": "gemini-2.0-flash-exp", "analysis_stage": "structured_extraction", "extraction_method": "langextract_gemini", "extraction_passes": 2, "extraction_timestamp": "2025-09-07T07:19:25.920951", "character_level_positioning": true}	active	{}	2025-09-07 07:19:25.921554-04
dedd6994-64b2-44c9-b448-26b3817d6677	langextract_document_analysis	2025-09-07 07:24:36.766805-04	2025-09-07 07:24:36.771008-04	ed8306b9-db79-4e8a-b912-4abc776661a9	{"document_id": 70, "text_length": 112006, "gemini_model": "gemini-2.0-flash-exp", "analysis_stage": "structured_extraction", "extraction_method": "langextract_gemini", "extraction_passes": 2, "extraction_timestamp": "2025-09-07T07:24:36.766794", "character_level_positioning": true}	completed	{}	2025-09-07 07:24:36.767513-04
bf613619-f00d-4144-b6e0-cc85f80cfb9f	langextract_document_analysis	2025-09-07 07:32:27.954372-04	2025-09-07 07:32:27.957475-04	ed8306b9-db79-4e8a-b912-4abc776661a9	{"document_id": 69, "text_length": 18473, "gemini_model": "gemini-2.0-flash-exp", "analysis_stage": "structured_extraction", "extraction_method": "langextract_gemini", "extraction_passes": 2, "extraction_timestamp": "2025-09-07T07:32:27.954362", "character_level_positioning": true}	completed	{}	2025-09-07 07:32:27.954986-04
86a6c715-facb-44a3-bed6-e624f4dc91c1	langextract_document_analysis	2025-09-07 07:40:18.309462-04	2025-09-07 07:40:18.312374-04	ed8306b9-db79-4e8a-b912-4abc776661a9	{"document_id": 69, "text_length": 18473, "gemini_model": "gemini-2.0-flash-exp", "analysis_stage": "structured_extraction", "extraction_method": "langextract_gemini", "extraction_passes": 2, "extraction_timestamp": "2025-09-07T07:40:18.309451", "character_level_positioning": true}	completed	{}	2025-09-07 07:40:18.310056-04
62afbeb1-5505-41ad-99b1-b35b29e18a30	langextract_document_analysis	2025-09-07 07:45:58.163112-04	2025-09-07 07:45:58.163138-04	ed8306b9-db79-4e8a-b912-4abc776661a9	{"model_id": "gemini-1.5-flash", "document_id": 69, "text_length": 18473, "analysis_stage": "structured_extraction", "temp_file_source": true, "extraction_method": "langextract_gemini"}	completed	{}	2025-09-07 07:45:58.163733-04
990c7883-3a72-4ef8-a501-b34bbb223a2b	llm_orchestration_coordination	2025-09-07 07:45:58.169342-04	2025-09-07 07:45:58.169636-04	f1dc1456-50ee-4889-afa7-08760e2243f2	{"analysis_stage": "orchestration_planning", "tools_selected": ["spacy_nlp", "basic_tokenization"], "temp_file_source": true, "input_activity_id": "62afbeb1-5505-41ad-99b1-b35b29e18a30", "orchestration_stage": "tool_selection_and_coordination", "orchestration_method": "fallback_rules"}	completed	{}	2025-09-07 07:45:58.169763-04
\.


--
-- TOC entry 4412 (class 0 OID 43548)
-- Dependencies: 269
-- Data for Name: prov_agents; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.prov_agents (agent_id, agent_type, foaf_name, foaf_givenname, foaf_mbox, foaf_homepage, agent_metadata, created_at, updated_at) FROM stdin;
ed8306b9-db79-4e8a-b912-4abc776661a9	SoftwareAgent	LangExtract Gemini	\N	\N	\N	{"version": "1.0.9", "model_id": "gemini-2.0-flash-exp", "tool_type": "document_analyzer", "capabilities": ["structured_extraction", "character_positioning", "semantic_analysis"], "model_provider": "google"}	2025-09-06 22:55:41.400132-04	2025-09-06 22:55:41.400132-04
00496711-20b3-4c23-9d22-b7ea10482508	SoftwareAgent	OntExtract System	\N	\N	\N	{"version": "1.0.0", "features": ["JCDL", "period_aware", "human_in_loop"], "system_type": "ontology_integration"}	2025-09-06 22:55:41.400132-04	2025-09-06 22:55:41.400132-04
80150cbd-871d-418d-9b04-8b7fdcd1ad26	SoftwareAgent	LLM Orchestrator	\N	\N	\N	{"version": "1.0.0", "providers": ["anthropic", "openai", "google"], "capabilities": ["tool_routing", "synthesis", "quality_control"], "orchestrator_type": "multi_provider_llm"}	2025-09-06 22:55:41.400132-04	2025-09-06 22:55:41.400132-04
408e0e46-1358-44a6-8941-4aec4d122267	Person	researcher:1	\N	\N	\N	{"role": "researcher"}	2025-09-07 07:00:57.168086-04	2025-09-07 07:00:57.168089-04
64d5d79a-8a34-4325-af1b-f472206b5cc8	SoftwareAgent	orchestrator_anthropic	\N	\N	\N	{"version": "1.0", "model_id": "claude-3-5-sonnet-20241022", "tool_type": "llm_orchestrator", "capabilities": ["tool_selection", "analysis_coordination", "synthesis_planning"], "model_provider": "anthropic", "reliability_score": 0.9}	2025-09-07 07:19:25.932196-04	2025-09-07 07:19:25.932197-04
f1dc1456-50ee-4889-afa7-08760e2243f2	SoftwareAgent	orchestrator_google	\N	\N	\N	{"version": "1.0", "tool_type": "llm_orchestrator", "capabilities": ["tool_selection", "analysis_coordination", "synthesis_planning"], "model_provider": "google"}	2025-09-07 07:45:58.159743-04	2025-09-07 07:45:58.159745-04
\.


--
-- TOC entry 4414 (class 0 OID 43579)
-- Dependencies: 271
-- Data for Name: prov_entities; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.prov_entities (entity_id, entity_type, generatedattime, invalidatedattime, wasgeneratedby, wasattributedto, wasderivedfrom, entity_value, entity_metadata, character_start, character_end, created_at) FROM stdin;
c1f662cd-d87a-46a7-8e8c-52ca2844ec1c	langextract_document_extraction	2025-09-07 07:19:25.922532-04	\N	cbb11d95-287b-4235-b423-9d3d152e1562	ed8306b9-db79-4e8a-b912-4abc776661a9	\N	{"domain_indicators": [], "extraction_results": {"text_length": 50000, "extraction_method": "langextract_gemini", "orchestration_ready": true, "extraction_timestamp": "2025-09-07T07:19:25.918453", "structured_extractions": {"key_concepts": ["agency", "agent", "intentionality", "action", "causation", "mental states", "agency", "intentional action", "moral responsibility", "free will", "metaphysics of agency", "sense of agency", "reasons and causes", "situationism", "automaticity", "dual-system theory", "perception and attention", "causal relationships", "agency", "intentional actions", "philosophy of action", "action", "intentionality", "intentional action", "action", "intentionality", "individuation of actions", "standard conception", "standard theory", "intentional action", "reason explanation", "mental states", "events", "causation", "reason explanation", "means-end rationale", "causal theory of action", "event-causal theory", "standard conception", "non-causal theories", "dual standpoint theories", "agency", "intentional action", "standard conception of action", "functional organization", "mental states", "events", "desires", "beliefs", "intentions", "causal relations", "deviant causal chains", "reasons for actions", "reasons", "mental states", "events", "agency", "initiation of action", "intentional actions", "causation", "desire-belief pairs", "intentions", "spontaneous action", "agency", "agent-causation", "intentional agency", "first-order desires", "second-order desires", "hierarchical account of agency", "standard theory", "mental attitude", "agency", "intentional actions", "human agency", "moral responsibility", "agency", "mental representations", "intentional mental states", "representational mental states", "predictive success", "mental states", "agency", "realism", "representational contents", "philosophy of mind", "cognitive science", "mental representation", "linguistic competence", "representational mental states", "desires", "drives", "intentionality", "agency", "representational mental states", "practical reasoning", "intentional agency", "unintentional agency", "minimal agency", "adaptive regulation", "metabolic self-maintenance", "goal-directed behavior", "intrinsic goal", "human agency", "representational mental states", "embodied and enactive approaches", "skilled coping", "mental representations", "mental representation", "behavioral dispositions", "skilled coping", "representational mental states", "standard theory", "motor schemata", "personal-level mental states", "intentional vacuum", "long-term goals and intentions", "agency", "representational mental states", "embodied cognition", "intentional agency", "unintentional agency", "mental representation", "temporally extended planning agency", "agency", "mental agency", "shared agency", "collective agency", "relational agency", "artificial agency", "intentional action", "intentionality", "agency theory", "moral responsibility", "ethical frameworks", "mental actions", "decision-making", "intentional action", "unintentional action", "intentional action", "reason explanation", "remembering", "intentional mental action", "deliberative activity", "mental agency", "evaluative control", "voluntary control", "volitionist theories of agency", "epistemic agency", "indirect doxastic voluntarism", "direct doxastic voluntarism", "belief revision", "doxastic voluntarism", "shared agency", "collective agency", "intentional actions", "reason-responsiveness", "collective agency", "mental states", "relational agency", "autonomy", "feminist critiques", "interpersonal relationships", "artificial intelligence", "agency", "realist positions", "artificial systems", "intentional agency", "minimal agency", "agency", "metaphysics of agency", "event-causal approach", "agent-causal", "volitionist framework", "dual standpoint theory", "agency", "event-causal history", "agent-causal history", "volitions", "substance-causation", "agent-causal power", "event-causal framework", "naturalism", "substance-causation", "teleology", "agent-causal theories", "volitionist theories", "agency", "volitions", "substance", "causal powers", "agent’s exercise of control", "volitions", "event-causal framework", "mental attitudes", "actions", "deviant causal chains", "intentional action", "basic deviance", "consequential deviance", "basic deviance", "agency", "intention", "basic actions", "non-basic actions"], "temporal_markers": ["Winter 2019", "Aug 10, 2015", "Oct 28, 2019", "past few decades", "long history", "Hume and Aristotle", "contemporary analytic philosophy", "1957", "1963", "more recent debate", "Winter 2019", "Anscombe 1957", "Davidson 1963", "Goldman 1970", "Ginet 1990", "1963", "1970", "1970", "1986", "1987", "1976", "1984", "1989", "1992", "2003", "2003", "2003", "2010b", "Winter 2019", "1961", "1990", "2000", "2005", "1963", "1970", "2003", "2003", "1998", "2003", "2007", "1970", "1971", "1988", "1984", "1987", "1989", "1992", "2003", "2003", "1990", "2000", "2008", "1998", "2003", "2003", "Winter 2019", "1971", "1977", "1975", "1992", "2000", "2001", "1987", "2004", "2017", "2003", "1995", "2007", "1944", "1987", "Winter 2019", "1982", "1997", "2001", "1957", "1970", "2009", "1974", "Winter 2019 Edition 13", "Dreyfus 1991", "Markus Schlosser 2002", "Brooks 1991", "Beer 1995", "2009", "2011", "2014", "1987", "2000", "1994", "2018", "Winter 2019", "1957", "post-war period", "2003", "1997", "2009b", "Winter 2019", "2009b", "2015", "2009", "1990", "1998", "2008", "past two decades", "Winter 2019", "2009", "1987", "2009", "Winter 2019", "Davidson 1963", "1971", "Goldman 1970", "Brand 1984", "Bratman 1987", "Dretske 1988", "Bishop 1989", "Mele 1992", "2003", "Enç 2003", "Chisholm 1964", "Taylor 1966", "O’Connor 2000", "Clarke 2003", "Lowe 2008", "Ginet 1990", "McCann 1998", "1952", "2003", "1971", "2010", "1949", "1950s and 60s", "2000", "2003", "1959", "1961", "1963", "1963", "1970", "Winter 2019", "1973"], "domain_indicators": ["philosophy", "philosophy of action", "metaphysics", "philosophy", "psychology", "cognitive neuroscience", "social science", "anthropology", "ethics", "meta-ethics", "philosophy", "analytic philosophy", "agency theory", "Stanford Encyclopedia of Philosophy", "philosophy of action", "philosophy of mind", "philosophy of mind", "philosophy of psychology", "ethics", "meta-ethics", "philosophy of action", "practical reasoning", "long-term planning", "philosophy of mind", "philosophy of action", "causality", "epistemology", "metaphysics", "philosophy", "action theory", "agency theory", "philosophy", "philosophy of action", "agency theory", "moral psychology", "philosophy", "metaphysics", "Stanford Encyclopedia of Philosophy", "philosophy", "agency theory", "moral philosophy", "action theory", "philosophy", "ethics", "moral psychology", "philosophy", "cognitive science", "psychology", "philosophy", "cognitive science", "psychology", "behavioral science", "philosophy", "cognitive science", "artificial intelligence", "philosophy of mind", "cognitive science", "robotics", "dynamical systems theory", "cognitive science", "philosophy of mind", "philosophy of mind", "cognitive science", "artificial intelligence", "philosophy", "cognitive science", "philosophy", "ethics", "philosophy of action", "philosophy of mind", "epistemology", "philosophy", "epistemology", "agency theory", "philosophy", "feminist theory", "artificial intelligence", "ethics", "philosophy", "artificial intelligence", "cognitive science", "metaphysics", "philosophy", "metaphysics", "action theory", "agency theory", "philosophy of mind", "philosophy of action", "metaphysics", "epistemology", "philosophy", "agency theory", "causality", "ethics", "philosophy", "ethics", "moral psychology"], "recommended_tools": ["semantic_analysis", "named_entity_recognition", "topic_modeling", "topic modeling", "semantic network analysis", "text mining", "knowledge graph construction", "historical_nlp", "philosophical_terminology", "concept_mapping", "network_analysis", "semantic analysis", "named entity recognition", "relation extraction", "semantic_analysis", "named_entity_recognition", "topic_modeling", "temporal_analysis", "semantic_role_labeling", "causal_inference", "philosophical_text_analysis", "temporal_relation_extraction", "semantic_analysis", "concept_mapping", "knowledge_graph", "semantic_role_labeling", "named_entity_recognition", "relation_extraction", "citation_analysis", "NLP", "semantic analysis", "philosophical terminology analysis", "semantic_role_labeling", "named_entity_recognition", "coref_resolution", "topic_modeling", "semantic_role_labeling", "named_entity_recognition", "co-reference_resolution", "sentiment_analysis", "semantic analysis", "concept mapping", "network analysis", "semantic analysis", "named entity recognition", "topic modeling", "temporal analysis", "NLP", "semantic analysis", "knowledge graph", "temporal analysis", "semantic_analysis", "concept_mapping", "temporal_analysis", "network_analysis", "semantic analysis", "discourse analysis", "concept mapping", "topic modeling", "named entity recognition", "relation extraction", "citation analysis", "semantic analysis", "concept mapping", "network analysis", "historical_nlp", "philosophical_terminology", "temporal_analysis", "semantic_role_labeling", "semantic role labeling", "named entity recognition", "relation extraction", "topic modeling", "semantic analysis", "topic modeling", "concept mapping", "semantic analysis", "topic modeling", "sentiment analysis", "named entity recognition", "semantic analysis", "philosophical terminology analysis", "concept mapping", "knowledge graph construction", "named entity recognition", "relationship extraction", "topic modeling", "citation analysis", "semantic_role_labeling", "named_entity_recognition", "relation_extraction", "topic_modeling", "temporal analysis", "philosophical terminology analysis", "causal inference", "concept mapping", "text_mining", "semantic_analysis", "concept_extraction"], "document_structure": [], "character_positions": true, "processing_priority": "academic_high", "analytical_complexity": "medium", "extraction_confidence": 0.0, "orchestration_metadata": {"stage": "langextract_completed", "ready_for_orchestration": true, "tool_routing_confidence": 0.0, "expected_processing_time": "extended"}}}, "key_concepts_count": 0, "extraction_timestamp": "2025-09-07T07:19:25.922536", "extraction_confidence": 0.5, "temporal_markers_count": 0, "character_level_positions": true}	{}	\N	\N	2025-09-07 07:19:25.923142-04
c8ca3489-24e2-4f68-b96e-4a84a2671a2f	langextract_document_extraction	2025-09-07 07:24:36.768482-04	\N	dedd6994-64b2-44c9-b448-26b3817d6677	ed8306b9-db79-4e8a-b912-4abc776661a9	\N	{"domain_indicators": [], "extraction_results": {"text_length": 50000, "extraction_method": "langextract_gemini", "orchestration_ready": true, "extraction_timestamp": "2025-09-07T07:24:36.763897", "structured_extractions": {"key_concepts": ["agency", "agent", "intentionality", "action", "causation", "mental states", "agency", "intentional action", "mental representations", "free will", "moral responsibility", "metaphysics of agency", "sense of agency", "reasons and causes", "situationism", "automaticity", "dual-system theory", "perception and attention", "causal relationships", "agency", "intentional actions", "philosophy of action", "action", "intentionality", "intentional action", "action", "intentionality", "individuation of actions", "intentionality", "acting intentionally", "acting for a reason", "agency", "practical reasoning", "long-term planning", "standard conception", "desire-belief", "practical syllogism", "intentions", "standard conception", "standard theory", "intentional action", "reason explanation", "mental states", "events", "causation", "reason explanation", "means-end rationale", "causal theory of action", "event-causal theory", "standard conception", "non-causal theories", "causally efficacious mental states", "dual standpoint theories", "agency", "intentional action", "standard conception of action", "functional organization", "mental states", "events", "desires", "beliefs", "intentions", "causal relations", "deviant causal chains", "reasons for actions", "reasons", "mental states", "events", "agency", "initiation of action", "intentional actions", "causation", "desire-belief pairs", "intentions", "spontaneous action", "reasons", "intentions", "agency", "agent-causation", "intentional agency", "first-order desires", "second-order desires", "hierarchical account of agency", "intentionality", "agency theory", "moral responsibility", "ethical frameworks", "agent-causation", "self-governance", "practical deliberation", "standard theory", "mental attitude", "agency", "intentional actions", "human agency", "moral responsibility", "agency", "mental representations", "intentional mental states", "representational mental states", "predictive success", "mental states", "agency", "realism", "representational content", "philosophy of mind", "cognitive science", "mental representation", "linguistic competence", "desires", "drives", "intentionality", "agency", "representational mental states", "practical reasoning", "intentional agency", "unintentional agency", "minimal agency", "adaptive regulation", "metabolic self-maintenance", "goal-directed behavior", "intrinsic goal", "human agency", "representational mental states", "embodied and enactive approaches", "skillful and “online” engagement", "skilled coping", "mental representations", "mental representation", "behavioral dispositions", "skilled coping", "representational mental states", "standard theory", "motor schemata", "personal-level mental states", "intentional vacuum", "long-term goals", "agency", "representational mental states", "embodied cognition", "intentional agency", "unintentional agency", "mental representation", "temporally extended planning agency", "agency", "self-controlled agency", "autonomous agency", "free agency", "representational mental states", "mental agency", "shared agency", "collective agency", "relational agency", "artificial agency", "intentional action", "decision-making", "intentionality", "agency theory", "moral responsibility", "ethical frameworks", "mental actions", "decision-making", "intentional action", "unintentional action", "intentional action", "reason explanation", "remembering", "intentional mental action", "deliberative activity", "mental agency", "evaluative control", "voluntary control", "volitionist theories of agency", "epistemic agency", "indirect doxastic voluntarism", "direct doxastic voluntarism", "belief revision", "doxastic voluntarism", "shared agency", "collective agency", "intentional actions", "reason-responsiveness", "collective agency", "mental states", "relational agency", "autonomy", "feminist critiques", "interpersonal relationships", "artificial intelligence", "agency", "realist positions", "artificial systems", "intentional agency", "minimal agency", "agency", "metaphysics of agency", "event-causal approach", "agent-causal", "volitionist framework", "dual standpoint theory", "agency", "event-causal history", "agent-causal history", "volitions", "substance-causation", "agent-causal power", "event-causal framework", "naturalism", "substance-causation", "teleology", "agent-causal theories", "volitionist theories of agency", "volitions", "actions sui generis", "agent’s exercise of control", "volitions", "event-causal framework", "mental attitudes", "actions", "deviant causal chains", "intentional action", "basic deviance", "consequential deviance", "primary deviance", "secondary deviance", "basic deviance", "agency", "intention", "action"], "temporal_markers": ["Winter 2019", "Aug 10, 2015", "Oct 28, 2019", "past few decades", "long history", "Hume and Aristotle", "contemporary analytic philosophy", "1957", "1963", "more recent debate", "Winter 2019", "Anscombe 1957", "Davidson 1963", "Goldman 1970", "Ginet 1990", "1963", "1970", "1970", "1986", "1987", "1976", "1984", "1989", "1992", "2003", "2003", "2003", "2010b", "Winter 2019", "1961", "1990", "2000", "2005", "1963", "1970", "2003", "2003", "1998", "2003", "2007", "1970", "1971", "1988", "1984", "1987", "1989", "1992", "2003", "2003", "1990", "2000", "2008", "1998", "2003", "2003", "Winter 2019", "1971", "1977", "1975", "1992", "2000", "2001", "1987", "2004", "2017", "2003", "1995", "2007", "1944", "1987", "Winter 2019", "1982", "1997", "2001", "1957", "1970", "2009", "1974", "Dreyfus 1991", "Markus Schlosser\\nWinter 2019 Edition 13\\n2002", "Brooks 1991", "Beer 1995", "2009", "2011", "2014", "1987", "2000", "1994", "2018", "Winter 2019", "1957", "post-war period", "2003", "1997", "2009b", "Winter 2019", "2009b", "2015", "2009", "1990", "1998", "2008", "section 3.1", "past two decades", "Winter 2019", "2009", "1987", "2009", "Winter 2019", "Davidson 1963", "1971", "Goldman 1970", "Brand 1984", "Bratman 1987", "Dretske 1988", "Bishop 1989", "Mele 1992", "2003", "Enç 2003", "Chisholm 1964", "Taylor 1966", "O’Connor 2000", "Clarke 2003", "Lowe 2008", "Ginet 1990", "McCann 1998", "1952", "2003", "1971", "2010", "1949", "1950s and 60s", "2000", "2003", "1959", "1961", "1963", "1963", "1970", "Winter 2019", "1973"], "domain_indicators": ["philosophy", "philosophy of action", "metaphysics", "philosophy", "psychology", "cognitive neuroscience", "social science", "anthropology", "ethics", "meta-ethics", "philosophy of mind", "philosophy of psychology", "philosophy", "analytic philosophy", "agency theory", "philosophy of action", "philosophy of mind", "philosophy of mind", "philosophy of psychology", "ethics", "meta-ethics", "philosophy of action", "Stanford Encyclopedia of Philosophy", "philosophy of mind", "philosophy of action", "epistemology", "metaphysics", "philosophy", "action theory", "agency theory", "philosophy", "philosophy of action", "agency theory", "moral psychology", "philosophy", "metaphysics", "Stanford Encyclopedia of Philosophy", "philosophy", "ethics", "action theory", "philosophy", "ethics", "action theory", "philosophy", "cognitive science", "psychology", "philosophy", "cognitive science", "psychology", "behavioral science", "philosophy", "cognitive science", "artificial intelligence", "philosophy of mind", "cognitive science", "robotics", "dynamical systems theory", "cognitive science", "philosophy of mind", "philosophy of mind", "cognitive science", "artificial intelligence", "philosophy", "cognitive science", "artificial intelligence", "philosophy", "ethics", "philosophy of action", "philosophy of mind", "epistemology", "philosophy", "epistemology", "agency theory", "philosophy", "feminist theory", "artificial intelligence", "ethics", "philosophy", "artificial intelligence", "cognitive science", "metaphysics", "philosophy", "metaphysics", "action theory", "agency theory", "philosophy of mind", "philosophy of action", "agency", "causation", "philosophy", "agency theory", "causality", "ethics", "philosophy", "ethics", "moral psychology"], "recommended_tools": ["semantic analysis", "topic modeling", "named entity recognition", "topic modeling", "keyword extraction", "semantic network analysis", "citation analysis", "historical_nlp", "philosophical_terminology", "concept_mapping", "network_analysis", "NLP", "semantic analysis", "text mining", "semantic_role_labeling", "named_entity_recognition", "relation_extraction", "coref_resolution", "topic_modeling", "semantic role labeling", "named entity recognition", "relation extraction", "text summarization", "semantic_role_labeling", "relation_extraction", "concept_mapping", "semantic_analysis", "named_entity_recognition", "relation_extraction", "citation_analysis", "NLP", "semantic analysis", "philosophical terminology analysis", "semantic_analysis", "philosophical_reasoning", "temporal_analysis", "citation_analysis", "semantic_role_labeling", "named_entity_recognition", "co-reference_resolution", "philosophical_text_analysis", "semantic_analysis", "concept_mapping", "network_analysis", "semantic analysis", "named entity recognition", "temporal analysis", "topic modeling", "semantic_analysis", "named_entity_recognition", "temporal_relation_extraction", "concept_mapping", "NLP", "semantic analysis", "topic modeling", "citation analysis", "semantic analysis", "concept mapping", "argument mining", "topic modeling", "named entity recognition", "relationship extraction", "citation analysis", "semantic analysis", "concept mapping", "network analysis", "historical_nlp", "philosophical_terminology", "temporal_analysis", "semantic_role_labeling", "named entity recognition", "relationship extraction", "topic modeling", "sentiment analysis", "semantic analysis", "concept mapping", "network analysis", "semantic analysis", "topic modeling", "named entity recognition", "sentiment analysis", "semantic analysis", "philosophical terminology analysis", "named entity recognition", "named entity recognition", "relationship extraction", "topic modeling", "citation analysis", "semantic_role_labeling", "named_entity_recognition", "coref_resolution", "relation_extraction", "temporal analysis", "philosophical terminology analysis", "causal inference", "concept mapping", "text_mining", "concept_extraction", "sentiment_analysis"], "document_structure": [], "character_positions": true, "processing_priority": "academic_high", "analytical_complexity": "medium", "extraction_confidence": 0.0, "orchestration_metadata": {"stage": "langextract_completed", "ready_for_orchestration": true, "tool_routing_confidence": 0.0, "expected_processing_time": "extended"}}}, "key_concepts_count": 0, "extraction_timestamp": "2025-09-07T07:24:36.768485", "extraction_confidence": 0.5, "temporal_markers_count": 0, "character_level_positions": true}	{}	\N	\N	2025-09-07 07:24:36.76917-04
4605ffb1-f688-4fbc-b42f-3d7ed2c4d84b	langextract_document_extraction	2025-09-07 07:32:27.955771-04	\N	bf613619-f00d-4144-b6e0-cc85f80cfb9f	ed8306b9-db79-4e8a-b912-4abc776661a9	\N	{"domain_indicators": [], "extraction_results": {"text_length": 18473, "extraction_method": "langextract_gemini", "orchestration_ready": true, "extraction_timestamp": "2025-09-07T07:32:27.951536", "structured_extractions": {"key_concepts": ["agent", "agency", "principal", "power of attorney", "patent agent", "agent of necessity", "electronic agent", "apparent agent", "ostensible agent", "implied agent", "associate agent", "patent agent", "bail-enforcement agent", "bounty hunter", "bargaining agent", "labor union", "collective bargaining", "broker-agent", "broker", "business agent", "case agent", "clearing agent", "securities transaction", "custodian of securities", "closing agent", "settlement agent", "settlement attorney", "coagent", "dual agent", "common agent", "commercial agent", "consular officer", "mercantile agent", "commission agent", "commission agent", "common agent", "corporate agent", "del credere agent", "diplomatic agent", "double agent", "dual agent", "emigrant agent", "fiscal agent", "foreign agent", "forwarding agent", "general agent", "government agent", "gratuitous agent", "high-managerial agent", "implied agent", "independent agent", "innocent agent", "principal", "agent", "compensation", "corporate policy", "law-enforcement", "mens rea", "insurance", "agent", "principal", "legal accountability", "insurance agent", "Model Penal Code § 2.06(2)(a)", "jural agent", "land agent", "listing agent", "local agent", "managing agent", "managing general agent", "member's agent", "mercantile agent", "nonservant agent", "underwriting authority", "professional liability", "principal", "nonservant agent", "independent contractor", "independent agent", "servant", "ostensible agent", "apparent agent", "patent agent", "registered patent agent", "patent solicitor", "patent attorney", "policywriting agent", "underwriting agent", "primary agent", "subagent", "private agent", "process agent", "registered agent", "procuring agent", "public agent", "real-estate agent", "broker", "salesperson", "estate agent", "realtor", "real-estate broker", "record agent", "insurance agent", "registered agent", "process agent", "resident agent", "patent agent", "secret agent", "self-appointed agent", "selling agent", "listing agent", "settlement agent", "closing agent", "showing agent", "soliciting agent", "special agent", "general agent", "insurance", "local agent", "solicitor", "specially accredited agent", "statutory agent", "stock-transfer agent", "transfer agent", "subagent", "primary agent", "subordinate agent", "buyer's broker", "broker", "agency", "principal", "agent", "fiduciary duties", "subordinate agent", "superior agent", "successor agent", "transfer agent", "trustee-agent", "undercover agent", "underwriting agent", "coagents", "principal", "primary agent", "high-managerial agent", "stock-transfer agent", "policywriting agent", "managing agent", "member's agent", "Lloyd's underwriters", "settlor", "beneficiaries", "trust", "undisclosed agent", "undisclosed principal", "universal agent", "vice-commercial agent", "principal", "agent", "consular service", "commercial agent"], "temporal_markers": ["2024", "15c", "1952", "1990", "2002", "1857", "1823", "1993", "1935", "1937", "1922", "16c", "18c", "2024", "1812", "17c", "1819", "1822", "18c", "1935", "1881", "1874", "18c", "1938", "1837", "17c", "1805", "1822", "1957", "1866", "1927", "1804", "1812", "1954", "18c", "1920", "2024", "1859", "18c", "17c", "1886", "1954", "17c", "1844", "1809", "18c", "1839", "1952", "1901", "1855", "17c", "1888", "1844", "1873", "18c", "1952", "17c", "1934", "17c", "1850", "1930", "1905", "1863", "18c", "1800", "2024", "2024"], "domain_indicators": ["law", "legal", "dictionary", "patents", "contract", "emergency", "law", "legal", "patents", "securities", "labor relations", "real property", "international relations", "legal", "business", "history", "finance", "law", "business", "insurance", "law", "legal studies", "insurance", "real estate", "law", "legal", "agency", "torts", "contracts", "intellectual property", "patents", "real estate", "law", "real estate", "insurance", "law", "insurance", "legal", "business", "agency law", "corporate law", "insurance law", "trust law", "criminal law", "law", "legal", "consular affairs", "agency law"], "recommended_tools": ["legal_text_analysis", "named_entity_recognition", "temporal_relation_extraction", "named entity recognition", "temporal relation extraction", "relation extraction", "topic modeling", "keyword_extraction", "named_entity_recognition", "temporal_analysis", "keyword_extraction", "named_entity_recognition", "temporal_analysis", "named entity recognition", "temporal analysis", "legal terminology analysis", "keyword_extraction", "named_entity_recognition", "relationship_extraction", "temporal_analysis", "named entity recognition", "temporal relation extraction", "relation extraction", "keyword_extraction", "named_entity_recognition", "relationship_extraction", "temporal_analysis", "keyword_extraction", "named_entity_recognition", "temporal_relation_extraction", "legal_text_analysis", "named_entity_recognition", "temporal_relation_extraction"], "document_structure": [], "character_positions": true, "processing_priority": "academic_high", "analytical_complexity": "medium", "extraction_confidence": 0.0, "orchestration_metadata": {"stage": "langextract_completed", "ready_for_orchestration": true, "tool_routing_confidence": 0.0, "expected_processing_time": "extended"}}}, "key_concepts_count": 0, "extraction_timestamp": "2025-09-07T07:32:27.955774", "extraction_confidence": 0.5, "temporal_markers_count": 0, "character_level_positions": true}	{}	\N	\N	2025-09-07 07:32:27.956373-04
65c216d6-3d13-4e5b-8a44-9641fa13b465	langextract_document_extraction	2025-09-07 07:40:18.310825-04	\N	86a6c715-facb-44a3-bed6-e624f4dc91c1	ed8306b9-db79-4e8a-b912-4abc776661a9	\N	{"domain_indicators": [], "extraction_results": {"text_length": 18473, "extraction_method": "langextract_gemini", "orchestration_ready": true, "extraction_timestamp": "2025-09-07T07:40:18.306736", "structured_extractions": {"key_concepts": ["agent", "agency", "principal", "employee", "power of attorney", "patent agent", "agent of necessity", "agent by necessity", "apparent agent", "ostensible agent", "implied agent", "associate agent", "patent agent", "bail-enforcement agent", "bounty hunter", "bargaining agent", "labor union", "collective bargaining", "broker-agent", "broker", "business agent", "case agent", "clearing agent", "securities transaction", "custodian of securities", "closing agent", "settlement agent", "settlement attorney", "coagent", "dual agent", "common agent", "commercial agent", "consular officer", "mercantile agent", "commission agent", "commission agent", "common agent", "corporate agent", "del credere agent", "diplomatic agent", "double agent", "dual agent", "emigrant agent", "fiscal agent", "foreign agent", "forwarding agent", "general agent", "government agent", "gratuitous agent", "high-managerial agent", "implied agent", "independent agent", "innocent agent", "principal", "agent", "compensation", "corporate policy", "law-enforcement", "mens rea", "insurance", "agent", "principal", "agency law", "legal accountability", "insurance agent", "real-estate broker", "underwriting authority", "Model Penal Code § 2.06(2)(a)", "jural agent", "land agent", "listing agent", "local agent", "managing agent", "managing general agent", "member's agent", "mercantile agent", "nonservant agent", "commercial agent", "producer", "recording agent", "record agent", "selling agent", "showing agent", "business agent", "MGA", "principal", "nonservant agent", "independent contractor", "independent agent", "servant", "ostensible agent", "apparent agent", "patent agent", "registered patent agent", "patent solicitor", "patent attorney", "policywriting agent", "underwriting agent", "primary agent", "subagent", "private agent", "process agent", "registered agent", "procuring agent", "public agent", "real-estate agent", "broker", "salesperson", "estate agent", "realtor", "real-estate broker", "record agent", "insurance agent", "registered agent", "process agent", "resident agent", "patent agent", "secret agent", "self-appointed agent", "selling agent", "listing agent", "settlement agent", "closing agent", "showing agent", "soliciting agent", "special agent", "general agent", "insurance", "local agent", "solicitor", "specially accredited agent", "statutory agent", "stock-transfer agent", "transfer agent", "subagent", "primary agent", "subordinate agent", "buyer's broker", "broker", "agency", "principal", "agent", "third party", "fiduciary duties", "subordinate agent", "superior agent", "successor agent", "transfer agent", "trustee-agent", "undercover agent", "underwriting agent", "coagents", "principal", "primary agent", "high-managerial agent", "stock-transfer agent", "policywriting agent", "managing agent", "member's agent", "Lloyd's underwriters", "undisclosed agent", "undisclosed principal", "universal agent", "vice-commercial agent", "principal", "agent", "consular service", "commercial agent"], "temporal_markers": ["2024", "15c", "1952", "1990", "2002", "1857", "1823", "1993", "1935", "1937", "1922", "16c", "18c", "2024", "1812", "17c", "1819", "1822", "18c", "1935", "1881", "1874", "18c", "1938", "1837", "17c", "1805", "1822", "1957", "1866", "1927", "1804", "1812", "1954", "18c", "1920", "2024", "1859", "18c", "17c", "1886", "1954", "17c", "1844", "1809", "18c", "1839", "1952", "1901", "1855", "17c", "1888", "1844", "1873", "18c", "1952", "17c", "1934", "17c", "1850", "1930", "1905", "1863", "18c", "1800", "2024", "2024"], "domain_indicators": ["law", "legal", "patents", "contract law", "agency law", "law", "legal", "patents", "securities", "labor relations", "real property", "international relations", "legal", "business", "history", "finance", "law", "business", "insurance", "law", "legal studies", "insurance", "real estate", "business", "agency", "contract law", "legal", "law", "agency", "patent law", "real estate", "criminal law", "law", "real estate", "insurance", "law", "insurance", "legal", "business", "agency law", "corporate law", "insurance law", "trust law", "criminal law", "law", "legal history", "consular affairs"], "recommended_tools": ["legal_text_analysis", "named_entity_recognition", "temporal_relation_extraction", "named entity recognition", "temporal relation extraction", "relation extraction", "topic modeling", "keyword_extraction", "named_entity_recognition", "temporal_analysis", "keyword_extraction", "named_entity_recognition", "temporal_analysis", "named_entity_recognition", "relationship_extraction", "temporal_analysis", "legal_ontology_mapping", "named_entity_recognition", "relationship_extraction", "temporal_analysis", "named entity recognition", "temporal relation extraction", "relation extraction", "keyword_extraction", "named_entity_recognition", "relationship_extraction", "temporal_analysis", "keyword_extraction", "named_entity_recognition", "temporal_analysis", "topic_modeling", "legal_text_analysis", "historical_data_extraction", "named_entity_recognition"], "document_structure": [], "character_positions": true, "processing_priority": "academic_high", "analytical_complexity": "medium", "extraction_confidence": 0.0, "orchestration_metadata": {"stage": "langextract_completed", "ready_for_orchestration": true, "tool_routing_confidence": 0.0, "expected_processing_time": "extended"}}}, "key_concepts_count": 0, "extraction_timestamp": "2025-09-07T07:40:18.310829", "extraction_confidence": 0.5, "temporal_markers_count": 0, "character_level_positions": true}	{}	\N	\N	2025-09-07 07:40:18.311441-04
b3ec3325-dbd7-4d76-b0dc-9489b9e66b37	langextract_document_extraction	2025-09-07 07:45:58.165283-04	\N	62afbeb1-5505-41ad-99b1-b35b29e18a30	ed8306b9-db79-4e8a-b912-4abc776661a9	\N	{"domain_indicators": ["law", "legal", "patents", "contract law", "agency law", "law", "legal", "patents", "securities", "labor relations", "real property", "international relations", "legal", "business", "history", "finance", "law", "business", "insurance", "law", "legal studies", "insurance", "real estate", "business", "agency", "contract law", "legal", "law", "agency", "patent law", "real estate", "criminal law", "law", "real estate", "insurance", "law", "insurance", "legal", "business", "agency law", "corporate law", "insurance law", "trust law", "criminal law", "law", "legal history", "consular affairs"], "extraction_results": {"key_concepts": ["agent", "agency", "principal", "employee", "power of attorney", "patent agent", "agent of necessity", "agent by necessity", "apparent agent", "ostensible agent", "implied agent", "associate agent", "patent agent", "bail-enforcement agent", "bounty hunter", "bargaining agent", "labor union", "collective bargaining", "broker-agent", "broker", "business agent", "case agent", "clearing agent", "securities transaction", "custodian of securities", "closing agent", "settlement agent", "settlement attorney", "coagent", "dual agent", "common agent", "commercial agent", "consular officer", "mercantile agent", "commission agent", "commission agent", "common agent", "corporate agent", "del credere agent", "diplomatic agent", "double agent", "dual agent", "emigrant agent", "fiscal agent", "foreign agent", "forwarding agent", "general agent", "government agent", "gratuitous agent", "high-managerial agent", "implied agent", "independent agent", "innocent agent", "principal", "agent", "compensation", "corporate policy", "law-enforcement", "mens rea", "insurance", "agent", "principal", "agency law", "legal accountability", "insurance agent", "real-estate broker", "underwriting authority", "Model Penal Code § 2.06(2)(a)", "jural agent", "land agent", "listing agent", "local agent", "managing agent", "managing general agent", "member's agent", "mercantile agent", "nonservant agent", "commercial agent", "producer", "recording agent", "record agent", "selling agent", "showing agent", "business agent", "MGA", "principal", "nonservant agent", "independent contractor", "independent agent", "servant", "ostensible agent", "apparent agent", "patent agent", "registered patent agent", "patent solicitor", "patent attorney", "policywriting agent", "underwriting agent", "primary agent", "subagent", "private agent", "process agent", "registered agent", "procuring agent", "public agent", "real-estate agent", "broker", "salesperson", "estate agent", "realtor", "real-estate broker", "record agent", "insurance agent", "registered agent", "process agent", "resident agent", "patent agent", "secret agent", "self-appointed agent", "selling agent", "listing agent", "settlement agent", "closing agent", "showing agent", "soliciting agent", "special agent", "general agent", "insurance", "local agent", "solicitor", "specially accredited agent", "statutory agent", "stock-transfer agent", "transfer agent", "subagent", "primary agent", "subordinate agent", "buyer's broker", "broker", "agency", "principal", "agent", "third party", "fiduciary duties", "subordinate agent", "superior agent", "successor agent", "transfer agent", "trustee-agent", "undercover agent", "underwriting agent", "coagents", "principal", "primary agent", "high-managerial agent", "stock-transfer agent", "policywriting agent", "managing agent", "member's agent", "Lloyd's underwriters", "undisclosed agent", "undisclosed principal", "universal agent", "vice-commercial agent", "principal", "agent", "consular service", "commercial agent"], "temporal_markers": ["2024", "15c", "1952", "1990", "2002", "1857", "1823", "1993", "1935", "1937", "1922", "16c", "18c", "2024", "1812", "17c", "1819", "1822", "18c", "1935", "1881", "1874", "18c", "1938", "1837", "17c", "1805", "1822", "1957", "1866", "1927", "1804", "1812", "1954", "18c", "1920", "2024", "1859", "18c", "17c", "1886", "1954", "17c", "1844", "1809", "18c", "1839", "1952", "1901", "1855", "17c", "1888", "1844", "1873", "18c", "1952", "17c", "1934", "17c", "1850", "1930", "1905", "1863", "18c", "1800", "2024", "2024"], "domain_indicators": ["law", "legal", "patents", "contract law", "agency law", "law", "legal", "patents", "securities", "labor relations", "real property", "international relations", "legal", "business", "history", "finance", "law", "business", "insurance", "law", "legal studies", "insurance", "real estate", "business", "agency", "contract law", "legal", "law", "agency", "patent law", "real estate", "criminal law", "law", "real estate", "insurance", "law", "insurance", "legal", "business", "agency law", "corporate law", "insurance law", "trust law", "criminal law", "law", "legal history", "consular affairs"], "recommended_tools": ["legal_text_analysis", "named_entity_recognition", "temporal_relation_extraction", "named entity recognition", "temporal relation extraction", "relation extraction", "topic modeling", "keyword_extraction", "named_entity_recognition", "temporal_analysis", "keyword_extraction", "named_entity_recognition", "temporal_analysis", "named_entity_recognition", "relationship_extraction", "temporal_analysis", "legal_ontology_mapping", "named_entity_recognition", "relationship_extraction", "temporal_analysis", "named entity recognition", "temporal relation extraction", "relation extraction", "keyword_extraction", "named_entity_recognition", "relationship_extraction", "temporal_analysis", "keyword_extraction", "named_entity_recognition", "temporal_analysis", "topic_modeling", "legal_text_analysis", "historical_data_extraction", "named_entity_recognition"], "document_structure": [], "character_positions": true, "processing_priority": "academic_high", "analytical_complexity": "medium", "extraction_confidence": 0.0, "orchestration_metadata": {"stage": "langextract_completed", "ready_for_orchestration": true, "tool_routing_confidence": 0.0, "expected_processing_time": "extended"}}, "key_concepts_count": 168, "extraction_timestamp": "2025-09-07T07:45:58.166333", "extraction_confidence": 0.0, "temporal_markers_count": 67, "character_level_positions": true}	{}	\N	\N	2025-09-07 07:45:58.166984-04
\.


--
-- TOC entry 4415 (class 0 OID 43607)
-- Dependencies: 272
-- Data for Name: prov_relationships; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.prov_relationships (relationship_id, relationship_type, subject_id, subject_type, object_id, object_type, relationship_metadata, created_at) FROM stdin;
a80a847e-d90f-4d63-ac46-fb283a50605d	wasGeneratedBy	c1f662cd-d87a-46a7-8e8c-52ca2844ec1c	Entity	cbb11d95-287b-4235-b423-9d3d152e1562	Activity	{"created_automatically": true}	2025-09-07 07:19:25.924739-04
38af53a4-cbd8-401f-9538-bfc87b80721d	wasGeneratedBy	c8ca3489-24e2-4f68-b96e-4a84a2671a2f	Entity	dedd6994-64b2-44c9-b448-26b3817d6677	Activity	{"created_automatically": true}	2025-09-07 07:24:36.773763-04
df4a244e-b0cf-490a-a5f1-340a5a1d867d	wasGeneratedBy	4605ffb1-f688-4fbc-b42f-3d7ed2c4d84b	Entity	bf613619-f00d-4144-b6e0-cc85f80cfb9f	Activity	{"created_automatically": true}	2025-09-07 07:32:27.958732-04
048fdf41-10d5-4a09-b510-9a01b19e3448	wasGeneratedBy	65c216d6-3d13-4e5b-8a44-9641fa13b465	Entity	86a6c715-facb-44a3-bed6-e624f4dc91c1	Activity	{"created_automatically": true}	2025-09-07 07:40:18.313557-04
\.


--
-- TOC entry 4419 (class 0 OID 43690)
-- Dependencies: 277
-- Data for Name: provenance_activities; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.provenance_activities (id, prov_id, prov_type, prov_label, started_at_time, ended_at_time, was_associated_with, used_plan, processing_job_id, experiment_id, activity_type, activity_metadata, created_at, updated_at) FROM stdin;
1	activity_embeddings_73	ont:EmbeddingsProcessing	Embeddings generation for document 73	2025-09-07 15:14:53.080437	2025-09-07 15:14:54.890679	user_1	\N	\N	\N	embeddings	{"embedding_method": "local", "processing_start": "pending"}	2025-09-07 15:14:53.080439	2025-09-07 11:14:53.264988
2	activity_embeddings_74	ont:EmbeddingsProcessing	Embeddings generation for document 74	2025-09-07 15:24:01.567482	2025-09-07 15:24:04.356244	user_1	\N	\N	\N	embeddings	{"embedding_method": "local", "processing_start": "pending"}	2025-09-07 15:24:01.567483	2025-09-07 11:24:01.764896
3	activity_embeddings_75	ont:EmbeddingsProcessing	Embeddings generation for document 75	2025-09-07 16:56:50.470348	2025-09-07 16:56:53.340529	user_1	\N	\N	\N	embeddings	{"embedding_method": "local", "processing_start": "pending"}	2025-09-07 16:56:50.470349	2025-09-07 12:56:50.742344
4	activity_segmentation_76	ont:SegmentationProcessing	Document segmentation for document 76	2025-09-07 16:57:05.644725	2025-09-07 16:57:05.825441	user_1	\N	\N	\N	segmentation	{"overlap": 50, "chunk_size": 500, "processing_start": "pending", "segmentation_method": "paragraph"}	2025-09-07 16:57:05.644726	2025-09-07 12:57:05.824433
5	activity_embeddings_77	ont:EmbeddingsProcessing	Embeddings generation for document 77	2025-09-07 17:19:55.736445	2025-09-07 17:19:57.56835	user_1	\N	\N	\N	embeddings	{"embedding_method": "local", "processing_start": "pending"}	2025-09-07 17:19:55.736446	2025-09-07 13:19:55.810477
6	activity_segmentation_78	ont:SegmentationProcessing	Document segmentation for document 78	2025-09-07 17:20:20.77898	2025-09-07 17:20:20.855147	user_1	\N	\N	\N	segmentation	{"overlap": 50, "chunk_size": 500, "processing_start": "pending", "segmentation_method": "paragraph"}	2025-09-07 17:20:20.778982	2025-09-07 13:20:20.854392
7	activity_composite_81	ont:CompositeCreation	Creating composite document from 3 sources	2025-09-07 18:05:29.434315	2025-09-07 18:05:29.433741	user_1	\N	\N	\N	composite_creation	{"results": {"success": true, "composite_document_id": 81}, "strategy": "all_processing", "source_count": 3, "processing_types_aggregated": ["generate_embeddings", "segment_document"]}	2025-09-07 18:05:29.434316	2025-09-07 18:05:29.434316
8	activity_embeddings_82	ont:EmbeddingsProcessing	Embeddings generation for document 82	2025-09-07 19:38:38.065732	2025-09-07 19:38:41.588615	user_1	\N	\N	\N	embeddings	{"embedding_method": "local", "processing_start": "pending"}	2025-09-07 19:38:38.065734	2025-09-07 15:38:38.24393
9	activity_embeddings_83	ont:EmbeddingsProcessing	Embeddings generation for document 83	2025-09-07 20:41:55.067902	2025-09-07 20:41:57.280477	user_1	\N	\N	\N	embeddings	{"embedding_method": "local", "processing_start": "pending"}	2025-09-07 20:41:55.067903	2025-09-07 16:41:55.274718
10	activity_composite_84	ont:CompositeCreation	Creating composite document from 2 sources	2025-09-07 20:41:57.296899	2025-09-07 20:41:57.296778	user_1	\N	\N	\N	composite_creation	{"results": {"success": true, "composite_document_id": 84}, "strategy": "all_processing", "source_count": 2, "processing_types_aggregated": ["generate_embeddings"]}	2025-09-07 20:41:57.2969	2025-09-07 20:41:57.296901
11	activity_segmentation_85	ont:SegmentationProcessing	Document segmentation for document 85	2025-09-07 20:43:07.175931	2025-09-07 20:43:07.3314	user_1	\N	\N	\N	segmentation	{"overlap": 50, "chunk_size": 500, "processing_start": "pending", "segmentation_method": "paragraph"}	2025-09-07 20:43:07.175933	2025-09-07 16:43:07.330498
12	activity_embeddings_88	ont:EmbeddingsProcessing	Embeddings generation for document 88	2025-09-07 21:12:49.255326	2025-09-07 21:12:52.101167	user_1	\N	\N	\N	embeddings	{"embedding_method": "local", "processing_start": "pending"}	2025-09-07 21:12:49.255329	2025-09-07 17:12:49.537952
13	activity_segmentation_89	ont:SegmentationProcessing	Document segmentation for document 89	2025-09-07 21:18:03.034324	2025-09-07 21:18:03.112811	user_1	\N	\N	\N	segmentation	{"overlap": 50, "chunk_size": 500, "processing_start": "pending", "segmentation_method": "paragraph"}	2025-09-07 21:18:03.034326	2025-09-07 17:18:03.111834
14	activity_embeddings_90	ont:EmbeddingsProcessing	Embeddings generation for document 90	2025-09-07 21:22:11.624573	2025-09-07 21:22:13.337262	user_1	\N	\N	\N	embeddings	{"embedding_method": "local", "processing_start": "pending"}	2025-09-07 21:22:11.624575	2025-09-07 17:22:11.807038
15	activity_embeddings_91	ont:EmbeddingsProcessing	Embeddings generation for document 91	2025-09-07 21:27:45.333698	2025-09-07 21:27:47.521796	user_1	\N	\N	\N	embeddings	{"embedding_method": "local", "processing_start": "pending"}	2025-09-07 21:27:45.3337	2025-09-07 17:27:45.528519
16	activity_segmentation_92	ont:SegmentationProcessing	Document segmentation for document 92	2025-09-07 21:28:04.340785	2025-09-07 21:28:04.656585	user_1	\N	\N	\N	segmentation	{"overlap": 50, "chunk_size": 500, "processing_start": "pending", "segmentation_method": "paragraph"}	2025-09-07 21:28:04.340787	2025-09-07 17:28:04.655903
17	activity_embeddings_93	ont:EmbeddingsProcessing	Embeddings generation for document 93	2025-09-07 21:33:49.703296	2025-09-07 21:33:50.817317	user_1	\N	\N	\N	embeddings	{"embedding_method": "local", "processing_start": "pending"}	2025-09-07 21:33:49.703299	2025-09-07 17:33:49.931611
18	activity_segmentation_94	ont:SegmentationProcessing	Document segmentation for document 94	2025-09-07 21:34:21.415528	2025-09-07 21:34:21.56048	user_1	\N	\N	\N	segmentation	{"overlap": 50, "chunk_size": 500, "processing_start": "pending", "segmentation_method": "paragraph"}	2025-09-07 21:34:21.41553	2025-09-07 17:34:21.559801
19	activity_embeddings_95	ont:EmbeddingsProcessing	Embeddings generation for document 95	2025-09-07 21:36:36.518493	2025-09-07 21:36:38.346968	user_1	\N	\N	\N	embeddings	{"embedding_method": "local", "processing_start": "pending"}	2025-09-07 21:36:36.518495	2025-09-07 17:36:36.582597
20	activity_embeddings_96	ont:EmbeddingsProcessing	Embeddings generation for document 96	2025-09-07 21:38:05.034413	2025-09-07 21:38:06.727716	user_1	\N	\N	\N	embeddings	{"embedding_method": "local", "processing_start": "pending"}	2025-09-07 21:38:05.034415	2025-09-07 17:38:05.254757
21	activity_segmentation_98	ont:SegmentationProcessing	Document segmentation for document 98	2025-09-07 21:39:55.989824	2025-09-07 21:39:56.238161	user_1	\N	\N	\N	segmentation	{"overlap": 50, "chunk_size": 500, "processing_start": "pending", "segmentation_method": "paragraph"}	2025-09-07 21:39:55.989826	2025-09-07 17:39:56.237159
22	activity_embeddings_103	ont:EmbeddingsProcessing	Embeddings generation for document 103	2025-09-07 21:44:42.207339	2025-09-07 21:44:42.725125	user_1	\N	\N	\N	embeddings	{"embedding_method": "local", "processing_start": "pending"}	2025-09-07 21:44:42.207341	2025-09-07 17:44:42.359557
23	activity_segmentation_104	ont:SegmentationProcessing	Document segmentation for document 104	2025-09-07 21:48:35.689625	2025-09-07 21:48:35.920736	user_1	\N	\N	\N	segmentation	{"overlap": 50, "chunk_size": 500, "processing_start": "pending", "segmentation_method": "paragraph"}	2025-09-07 21:48:35.689628	2025-09-07 17:48:35.919908
24	activity_embeddings_105	ont:EmbeddingsProcessing	Embeddings generation for document 105	2025-09-07 21:56:03.878701	2025-09-07 21:56:04.54147	user_1	\N	\N	\N	embeddings	{"embedding_method": "local", "processing_start": "pending"}	2025-09-07 21:56:03.878703	2025-09-07 17:56:04.114228
25	activity_embeddings_107	ont:EmbeddingsProcessing	Embeddings generation for document 107	2025-09-07 21:58:26.758422	2025-09-07 21:58:29.085002	user_1	\N	\N	\N	embeddings	{"embedding_method": "local", "processing_start": "pending"}	2025-09-07 21:58:26.758425	2025-09-07 17:58:26.905645
26	activity_segmentation_108	ont:SegmentationProcessing	Document segmentation for document 108	2025-09-07 21:58:45.858361	2025-09-07 21:58:46.018856	user_1	\N	\N	\N	segmentation	{"overlap": 50, "chunk_size": 500, "processing_start": "pending", "segmentation_method": "paragraph"}	2025-09-07 21:58:45.858363	2025-09-07 17:58:46.017962
27	activity_embeddings_109	ont:EmbeddingsProcessing	Embeddings generation for document 109	2025-09-07 22:08:35.105767	2025-09-07 22:08:35.872286	user_1	\N	\N	\N	embeddings	{"embedding_method": "local", "processing_start": "pending"}	2025-09-07 22:08:35.105769	2025-09-07 18:08:35.376252
28	activity_embeddings_111	ont:EmbeddingsProcessing	Embeddings generation for document 111	2025-09-07 22:11:07.880891	2025-09-07 22:11:08.499712	user_1	\N	\N	\N	embeddings	{"embedding_method": "local", "processing_start": "pending"}	2025-09-07 22:11:07.880893	2025-09-07 18:11:08.173392
29	activity_embeddings_113	ont:EmbeddingsProcessing	Embeddings generation for document 113	2025-09-07 22:11:57.054778	2025-09-07 22:11:57.66995	user_1	\N	\N	\N	embeddings	{"embedding_method": "local", "processing_start": "pending"}	2025-09-07 22:11:57.05478	2025-09-07 18:11:57.241368
30	activity_embeddings_115	ont:EmbeddingsProcessing	Embeddings generation for document 115	2025-09-07 22:18:42.484526	2025-09-07 22:18:43.552261	user_1	\N	\N	\N	embeddings	{"embedding_method": "local", "processing_start": "pending"}	2025-09-07 22:18:42.484528	2025-09-07 18:18:42.727552
31	activity_segmentation_116	ont:SegmentationProcessing	Document segmentation for document 116	2025-09-07 23:50:50.013533	2025-09-07 23:50:50.2144	user_1	\N	\N	\N	segmentation	{"overlap": 50, "chunk_size": 500, "processing_start": "pending", "segmentation_method": "paragraph"}	2025-09-07 23:50:50.013535	2025-09-07 19:50:50.213225
\.


--
-- TOC entry 4387 (class 0 OID 19645)
-- Dependencies: 244
-- Data for Name: provenance_chains; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.provenance_chains (id, entity_id, entity_type, was_derived_from, derivation_activity, derivation_metadata, created_at) FROM stdin;
\.


--
-- TOC entry 4417 (class 0 OID 43676)
-- Dependencies: 275
-- Data for Name: provenance_entities; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.provenance_entities (id, prov_id, prov_type, prov_label, generated_at_time, invalidated_at_time, attributed_to_agent, derived_from_entity, generated_by_activity, document_id, experiment_id, version_number, version_type, prov_metadata, created_at, updated_at) FROM stdin;
23	document_104_v3	ont:Document	Clean Test Document (v3)	2025-09-07 21:48:35.690831	\N	user_1	\N	segmentation_processing	\N	\N	3	processed	{"language": null, "file_type": null, "word_count": 26, "content_type": "text"}	2025-09-07 21:48:35.690833	2025-09-07 17:55:51.052795
22	document_103_v2	ont:Document	Clean Test Document (v2)	2025-09-07 21:44:42.20789	\N	user_1	\N	embeddings_processing	\N	\N	2	processed	{"language": null, "file_type": null, "word_count": 26, "content_type": "text"}	2025-09-07 21:44:42.207892	2025-09-07 17:55:56.204104
24	document_105_v2	ont:Document	Clean Test Document (v2)	2025-09-07 21:56:03.879483	\N	user_1	\N	embeddings_processing	\N	\N	2	processed	{"language": null, "file_type": null, "word_count": 26, "content_type": "text"}	2025-09-07 21:56:03.879485	2025-09-07 18:08:19.618067
26	document_108_v3	ont:Document	Anscombe-Intention-1956 (v3)	2025-09-07 21:58:45.858655	\N	user_1	\N	segmentation_processing	\N	\N	3	processed	{"language": "en", "file_type": "pdf", "word_count": 4747, "content_type": "file"}	2025-09-07 21:58:45.858656	2025-09-07 18:08:23.247817
25	document_107_v2	ont:Document	Anscombe-Intention-1956 (v2)	2025-09-07 21:58:26.759479	\N	user_1	\N	embeddings_processing	\N	\N	2	processed	{"language": "en", "file_type": "pdf", "word_count": 4747, "content_type": "file"}	2025-09-07 21:58:26.759481	2025-09-07 18:08:27.759052
27	document_109_v2	ont:Document	Clean Test Document (v2)	2025-09-07 22:08:35.106419	\N	user_1	\N	embeddings_processing	\N	\N	2	processed	{"language": null, "file_type": null, "word_count": 26, "content_type": "text"}	2025-09-07 22:08:35.10642	2025-09-07 18:10:45.500299
28	document_111_v2	ont:Document	New test (v2)	2025-09-07 22:11:07.882651	\N	user_1	\N	embeddings_processing	\N	\N	2	processed	{"language": "en", "file_type": null, "word_count": 26, "content_type": "text"}	2025-09-07 22:11:07.882653	2025-09-07 18:11:38.709347
29	document_113_v2	ont:Document	Test (v2)	2025-09-07 22:11:57.055419	\N	user_1	\N	embeddings_processing	113	\N	2	processed	{"language": "en", "file_type": null, "word_count": 26, "content_type": "text"}	2025-09-07 22:11:57.055421	2025-09-07 22:11:57.055422
30	document_115_v2	ont:Document	Ground semantic (v2)	2025-09-07 22:18:42.485586	\N	user_1	\N	embeddings_processing	115	\N	2	processed	{"language": "en", "file_type": null, "word_count": 21, "content_type": "text"}	2025-09-07 22:18:42.485588	2025-09-07 22:18:42.485589
31	document_116_v3	ont:Document	Ground semantic (v3)	2025-09-07 23:50:50.018057	\N	user_1	\N	segmentation_processing	116	\N	3	processed	{"language": "en", "file_type": null, "word_count": 21, "content_type": "text"}	2025-09-07 23:50:50.018059	2025-09-07 23:50:50.01806
\.


--
-- TOC entry 4391 (class 0 OID 19817)
-- Dependencies: 248
-- Data for Name: search_history; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.search_history (id, query, query_type, results_count, execution_time, user_id, ip_address, created_at) FROM stdin;
\.


--
-- TOC entry 4385 (class 0 OID 19593)
-- Dependencies: 242
-- Data for Name: semantic_drift_activities; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.semantic_drift_activities (id, activity_type, start_period, end_period, temporal_scope_years, used_entity, generated_entity, was_associated_with, drift_metrics, detection_algorithm, algorithm_parameters, started_at_time, ended_at_time, activity_status, drift_detected, drift_magnitude, drift_type, evidence_summary, created_by, created_at) FROM stdin;
\.


--
-- TOC entry 4386 (class 0 OID 19628)
-- Dependencies: 243
-- Data for Name: term_version_anchors; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.term_version_anchors (id, term_version_id, context_anchor_id, similarity_score, rank_in_neighborhood, created_at) FROM stdin;
\.


--
-- TOC entry 4382 (class 0 OID 19524)
-- Dependencies: 239
-- Data for Name: term_versions; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.term_versions (id, term_id, temporal_period, temporal_start_year, temporal_end_year, meaning_description, context_anchor, original_context_anchor, fuzziness_score, confidence_level, certainty_notes, corpus_source, source_documents, extraction_method, generated_at_time, was_derived_from, derivation_type, version_number, is_current, created_by, created_at, neighborhood_overlap, positional_change, similarity_reduction, source_citation) FROM stdin;
377cf87f-c01f-4504-b5a1-5528d1a0171a	d36546b4-c1d1-4faa-aa7a-aec75e906917	1957_philosophy	1957	1967	Entity capable of deliberate action with moral responsibility. Anscombe establishes agency through intentional action, where agents bear capacity for purposeful acts distinguished from mere occurrences.	["intentional action", "moral responsibility", "deliberate choice", "purposeful acts", "philosophical agency"]	["intentionality", "moral_responsibility", "deliberate_action", "purposeful_behavior"]	\N	high	\N	\N	\N	manual_academic_curation	2025-09-06 00:24:36.30907-04	\N	\N	1	t	\N	2025-09-06 00:24:36.307794-04	\N	\N	\N	Anscombe, G.E.M. (1957). Intention. Oxford: Basil Blackwell.
41efa2ae-dcf1-4a7a-8d75-f0fccc4240da	d36546b4-c1d1-4faa-aa7a-aec75e906917	1976_economics	1976	1986	Party in contractual relationship who acts on behalf of a principal with potential conflicts of interest. Introduces principal-agent framework revolutionizing organizational theory.	["principal-agent relationship", "contractual authority", "information asymmetry", "moral hazard", "incentive alignment", "organizational theory"]	["contractual_authority", "information_asymmetry", "moral_hazard", "incentive_alignment"]	\N	high	\N	\N	\N	manual_academic_curation	2025-09-06 00:24:36.31156-04	\N	\N	1	t	\N	2025-09-06 00:24:36.311015-04	\N	\N	\N	Jensen, M.C. & Meckling, W.H. (1976). Theory of the firm: Managerial behavior, agency costs and ownership structure. Journal of Financial Economics, 3(4), 305-360.
397f8cfd-6a8a-4a67-b39f-8ea9ba086496	d36546b4-c1d1-4faa-aa7a-aec75e906917	1995_computer_science	1995	2005	Autonomous computational entity capable of independent action in dynamic environments. Marks transition from human role to independent computational artifact with properties of autonomy, reactivity, and social ability.	["artificial intelligence", "autonomous systems", "computational entities", "multi-agent systems", "intelligent behavior", "software agents"]	["autonomy", "reactivity", "social_ability", "computational_independence"]	\N	high	\N	\N	\N	manual_academic_curation	2025-09-06 00:24:36.312734-04	\N	\N	1	t	\N	2025-09-06 00:24:36.312371-04	\N	\N	\N	Wooldridge, M. & Jennings, N.R. (1995). Intelligent agents: Theory and practice. Knowledge Engineering Review, 10(2), 115-152.
2772abf8-6947-4aa7-a91e-2b0c7f40487f	d36546b4-c1d1-4faa-aa7a-aec75e906917	2018_machine_learning	2018	2028	Learning optimization entity that maximizes cumulative reward through environmental interaction. Agents defined by ability to learn from interaction, maintain state representations, and execute policies.	["reinforcement learning", "optimization", "reward maximization", "policy functions", "state representation", "value estimation", "learning systems"]	["reward_optimization", "environmental_interaction", "policy_execution", "state_representation"]	\N	high	\N	\N	\N	manual_academic_curation	2025-09-06 00:24:36.313767-04	\N	\N	1	t	\N	2025-09-06 00:24:36.31352-04	\N	\N	\N	Sutton, R.S. & Barto, A.G. (2018). Reinforcement Learning: An Introduction, 2nd Edition. MIT Press.
\.


--
-- TOC entry 4380 (class 0 OID 19487)
-- Dependencies: 237
-- Data for Name: terms; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.terms (id, term_text, entry_date, status, created_by, updated_by, created_at, updated_at, description, etymology, notes, research_domain, selection_rationale, historical_significance) FROM stdin;
d36546b4-c1d1-4faa-aa7a-aec75e906917	agent	2025-09-05 20:47:09.074219-04	active	4	\N	2025-09-05 20:47:09.074221-04	2025-09-05 20:24:36.302508-04	Semantic evolution across philosophy, economics, and computer science as documented in foundational academic works	\N	\N	interdisciplinary_academic	Key term showing semantic evolution across multiple disciplines	Evolves from philosophical concept to economic framework to AI systems
\.


--
-- TOC entry 4376 (class 0 OID 17857)
-- Dependencies: 233
-- Data for Name: text_segments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.text_segments (id, content, segment_type, segment_number, start_position, end_position, parent_segment_id, level, word_count, character_count, sentence_count, language, language_confidence, embedding, embedding_model, processed, processing_notes, topics, keywords, sentiment_score, complexity_score, created_at, updated_at, processed_at, document_id) FROM stdin;
110	Ground semantic evolution in foundational scholarly works across disciplines, using peer-reviewed literature rather than corpus statistics alone for authoritative meaning fixation.	paragraph	1	0	180	\N	0	21	180	1	en	\N	\N	\N	f	\N	\N	\N	\N	\N	2025-09-07 23:50:50.208353	2025-09-07 23:50:50.208356	\N	116
\.


--
-- TOC entry 4405 (class 0 OID 43281)
-- Dependencies: 262
-- Data for Name: tool_execution_logs; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.tool_execution_logs (id, orchestration_decision_id, tool_name, tool_version, execution_order, started_at, completed_at, execution_time_ms, execution_status, output_data, error_message, memory_usage_mb, cpu_usage_percent, output_quality_score) FROM stdin;
\.


--
-- TOC entry 4378 (class 0 OID 17863)
-- Dependencies: 235
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, username, email, password_hash, first_name, last_name, organization, is_active, is_admin, created_at, updated_at, last_login) FROM stdin;
2	test_user	test@example.com	scrypt:32768:8:1$7co0CsFaL4Ci2PCP$dbfb3c2a20be1aa55e7802d17fdc3ca43ae8fbf01b1602c3fc1a1a8f76106a38a34f945ea282d3b8e1f6fbfc30348a923141a097f9087c961bdf9595466590e9	\N	\N	\N	t	f	2025-08-11 14:05:08.556545	2025-08-11 14:05:08.55655	\N
5	demo_researcher	demo@ontextract.example	scrypt:32768:8:1$OhP5gkq9CsA1WFT0$dce3e9783fc98653cca9f6f9f35d1361ce90574a0723fa173771158d2c00ee85db627d503b221f8a1de6abf680deef400e38c36330336e42bfd590498ba25f9b	\N	\N	\N	t	f	2025-09-06 15:59:25.997463	2025-09-06 15:59:25.997466	\N
3	wook	wook@admin.local	scrypt:32768:8:1$TyCbt0YoZdyh6QjK$8651d05519b7732a13c23a115d1c660bf6e8d9b54565e81309f9263b7df5336956abb457801c820bbf9c79bb682ba1a9ee0267bf22d657c356e84ac867d92df6	Wook	Admin	\N	t	t	2025-08-20 09:18:26.897552	2025-08-23 21:26:13.020418	2025-08-20 09:22:56.630383
6	demo	demo@example.com	scrypt:32768:8:1$9jdXG3DOW2iGW8mR$4e6f70e527360e76c380380b07b15acc031d0642a3a0efcca8bcedcbe7e863aaa3853b8c84ffb4c2e2d1a6848cb791b29fae7f0c2bc29489348284420f4b0353	Demo	User	Digital Humanities Research	t	f	2025-09-06 17:03:46.269738	2025-09-06 17:03:46.26974	\N
1	chris	chris@example.com	scrypt:32768:8:1$WswwBUGGZdwwSmYD$415baa68963387f3d779be81dbf2f072e3e5aafab6dd30788759ebc938813396f5f09087baa629ddfa516784618ac33ac8952d29db17867991add0ff101d5b69	\N	\N	\N	t	t	2025-08-11 04:55:29.584732	2025-09-07 23:50:05.263283	2025-09-07 23:50:05.262192
4	system	system@ontextract.local	pbkdf2:sha256:600000$LfsdHmtQBeqlEewU$541edbd26b7797ee14b4e65cd8e75ac30e2e320bb2dc40cfeb6ce166c86ee088	\N	\N	\N	t	f	2025-09-05 20:47:09.065109	2025-09-05 20:47:09.065112	\N
\.


--
-- TOC entry 4423 (class 0 OID 49182)
-- Dependencies: 281
-- Data for Name: version_changelog; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.version_changelog (id, document_id, version_number, change_type, change_description, previous_version, created_at, created_by, processing_metadata) FROM stdin;
22	113	2	embeddings	Added embeddings processing to version 2	1	2025-09-07 18:11:57.044852	1	{"experiment_id": null, "embedding_method": "local", "processing_notes": "Embeddings processing using local method"}
23	115	2	embeddings	Added embeddings processing to version 2	1	2025-09-07 18:18:42.473087	1	{"experiment_id": null, "embedding_method": "local", "processing_notes": "Embeddings processing using local method"}
24	116	3	segmentation	Added segmentation processing to version 3	2	2025-09-07 19:50:49.990905	1	{"overlap": 50, "chunk_size": 500, "experiment_id": null, "processing_notes": "Document segmentation using paragraph method", "segmentation_method": "paragraph"}
\.


--
-- TOC entry 4517 (class 0 OID 0)
-- Dependencies: 255
-- Name: document_embeddings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: ontextract_user
--

SELECT pg_catalog.setval('public.document_embeddings_id_seq', 4, true);


--
-- TOC entry 4518 (class 0 OID 0)
-- Dependencies: 278
-- Name: document_processing_summary_id_seq; Type: SEQUENCE SET; Schema: public; Owner: ontextract_user
--

SELECT pg_catalog.setval('public.document_processing_summary_id_seq', 3, true);


--
-- TOC entry 4519 (class 0 OID 0)
-- Dependencies: 222
-- Name: documents_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.documents_id_seq', 116, true);


--
-- TOC entry 4520 (class 0 OID 0)
-- Dependencies: 245
-- Name: domains_id_seq; Type: SEQUENCE SET; Schema: public; Owner: ontextract_user
--

SELECT pg_catalog.setval('public.domains_id_seq', 1, false);


--
-- TOC entry 4521 (class 0 OID 0)
-- Dependencies: 267
-- Name: experiment_documents_v2_id_seq; Type: SEQUENCE SET; Schema: public; Owner: ontextract_user
--

SELECT pg_catalog.setval('public.experiment_documents_v2_id_seq', 24, true);


--
-- TOC entry 4522 (class 0 OID 0)
-- Dependencies: 226
-- Name: experiments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.experiments_id_seq', 1, false);


--
-- TOC entry 4523 (class 0 OID 0)
-- Dependencies: 228
-- Name: extracted_entities_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.extracted_entities_id_seq', 1, false);


--
-- TOC entry 4524 (class 0 OID 0)
-- Dependencies: 249
-- Name: ontologies_id_seq; Type: SEQUENCE SET; Schema: public; Owner: ontextract_user
--

SELECT pg_catalog.setval('public.ontologies_id_seq', 1, false);


--
-- TOC entry 4525 (class 0 OID 0)
-- Dependencies: 253
-- Name: ontology_entities_id_seq; Type: SEQUENCE SET; Schema: public; Owner: ontextract_user
--

SELECT pg_catalog.setval('public.ontology_entities_id_seq', 1, false);


--
-- TOC entry 4526 (class 0 OID 0)
-- Dependencies: 230
-- Name: ontology_mappings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.ontology_mappings_id_seq', 1, false);


--
-- TOC entry 4527 (class 0 OID 0)
-- Dependencies: 251
-- Name: ontology_versions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: ontextract_user
--

SELECT pg_catalog.setval('public.ontology_versions_id_seq', 1, false);


--
-- TOC entry 4528 (class 0 OID 0)
-- Dependencies: 232
-- Name: processing_jobs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.processing_jobs_id_seq', 29, true);


--
-- TOC entry 4529 (class 0 OID 0)
-- Dependencies: 276
-- Name: provenance_activities_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.provenance_activities_id_seq', 31, true);


--
-- TOC entry 4530 (class 0 OID 0)
-- Dependencies: 274
-- Name: provenance_entities_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.provenance_entities_id_seq', 31, true);


--
-- TOC entry 4531 (class 0 OID 0)
-- Dependencies: 247
-- Name: search_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: ontextract_user
--

SELECT pg_catalog.setval('public.search_history_id_seq', 1, false);


--
-- TOC entry 4532 (class 0 OID 0)
-- Dependencies: 234
-- Name: text_segments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.text_segments_id_seq', 110, true);


--
-- TOC entry 4533 (class 0 OID 0)
-- Dependencies: 236
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 6, true);


--
-- TOC entry 4534 (class 0 OID 0)
-- Dependencies: 280
-- Name: version_changelog_id_seq; Type: SEQUENCE SET; Schema: public; Owner: ontextract_user
--

SELECT pg_catalog.setval('public.version_changelog_id_seq', 24, true);


--
-- TOC entry 3957 (class 2606 OID 19516)
-- Name: analysis_agents analysis_agents_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.analysis_agents
    ADD CONSTRAINT analysis_agents_pkey PRIMARY KEY (id);


--
-- TOC entry 3983 (class 2606 OID 19580)
-- Name: context_anchors context_anchors_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.context_anchors
    ADD CONSTRAINT context_anchors_pkey PRIMARY KEY (id);


--
-- TOC entry 4035 (class 2606 OID 43149)
-- Name: document_embeddings document_embeddings_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.document_embeddings
    ADD CONSTRAINT document_embeddings_pkey PRIMARY KEY (id);


--
-- TOC entry 4131 (class 2606 OID 43782)
-- Name: document_processing_summary document_processing_summary_document_id_processing_type_sou_key; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.document_processing_summary
    ADD CONSTRAINT document_processing_summary_document_id_processing_type_sou_key UNIQUE (document_id, processing_type, source_document_id);


--
-- TOC entry 4133 (class 2606 OID 43780)
-- Name: document_processing_summary document_processing_summary_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.document_processing_summary
    ADD CONSTRAINT document_processing_summary_pkey PRIMARY KEY (id);


--
-- TOC entry 3907 (class 2606 OID 17885)
-- Name: documents documents_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (id);


--
-- TOC entry 4011 (class 2606 OID 19813)
-- Name: domains domains_name_key; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.domains
    ADD CONSTRAINT domains_name_key UNIQUE (name);


--
-- TOC entry 4013 (class 2606 OID 19815)
-- Name: domains domains_namespace_uri_key; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.domains
    ADD CONSTRAINT domains_namespace_uri_key UNIQUE (namespace_uri);


--
-- TOC entry 4015 (class 2606 OID 19809)
-- Name: domains domains_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.domains
    ADD CONSTRAINT domains_pkey PRIMARY KEY (id);


--
-- TOC entry 4017 (class 2606 OID 19811)
-- Name: domains domains_uuid_key; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.domains
    ADD CONSTRAINT domains_uuid_key UNIQUE (uuid);


--
-- TOC entry 3916 (class 2606 OID 17887)
-- Name: experiment_documents experiment_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.experiment_documents
    ADD CONSTRAINT experiment_documents_pkey PRIMARY KEY (experiment_id, document_id);


--
-- TOC entry 4086 (class 2606 OID 43420)
-- Name: experiment_documents_v2 experiment_documents_v2_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.experiment_documents_v2
    ADD CONSTRAINT experiment_documents_v2_pkey PRIMARY KEY (id);


--
-- TOC entry 3920 (class 2606 OID 17889)
-- Name: experiment_references experiment_references_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.experiment_references
    ADD CONSTRAINT experiment_references_pkey PRIMARY KEY (experiment_id, reference_id);


--
-- TOC entry 3924 (class 2606 OID 17891)
-- Name: experiments experiments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.experiments
    ADD CONSTRAINT experiments_pkey PRIMARY KEY (id);


--
-- TOC entry 3927 (class 2606 OID 17893)
-- Name: extracted_entities extracted_entities_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.extracted_entities
    ADD CONSTRAINT extracted_entities_pkey PRIMARY KEY (id);


--
-- TOC entry 3977 (class 2606 OID 19563)
-- Name: fuzziness_adjustments fuzziness_adjustments_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.fuzziness_adjustments
    ADD CONSTRAINT fuzziness_adjustments_pkey PRIMARY KEY (id);


--
-- TOC entry 4080 (class 2606 OID 43362)
-- Name: learning_patterns learning_patterns_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.learning_patterns
    ADD CONSTRAINT learning_patterns_pkey PRIMARY KEY (id);


--
-- TOC entry 4070 (class 2606 OID 43311)
-- Name: multi_model_consensus multi_model_consensus_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.multi_model_consensus
    ADD CONSTRAINT multi_model_consensus_pkey PRIMARY KEY (id);


--
-- TOC entry 4045 (class 2606 OID 43180)
-- Name: oed_definitions oed_definitions_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.oed_definitions
    ADD CONSTRAINT oed_definitions_pkey PRIMARY KEY (id);


--
-- TOC entry 4041 (class 2606 OID 43166)
-- Name: oed_etymology oed_etymology_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.oed_etymology
    ADD CONSTRAINT oed_etymology_pkey PRIMARY KEY (id);


--
-- TOC entry 4048 (class 2606 OID 43195)
-- Name: oed_historical_stats oed_historical_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.oed_historical_stats
    ADD CONSTRAINT oed_historical_stats_pkey PRIMARY KEY (id);


--
-- TOC entry 4050 (class 2606 OID 43197)
-- Name: oed_historical_stats oed_historical_stats_term_id_time_period_key; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.oed_historical_stats
    ADD CONSTRAINT oed_historical_stats_term_id_time_period_key UNIQUE (term_id, time_period);


--
-- TOC entry 4054 (class 2606 OID 43210)
-- Name: oed_quotation_summaries oed_quotation_summaries_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.oed_quotation_summaries
    ADD CONSTRAINT oed_quotation_summaries_pkey PRIMARY KEY (id);


--
-- TOC entry 4021 (class 2606 OID 19833)
-- Name: ontologies ontologies_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.ontologies
    ADD CONSTRAINT ontologies_pkey PRIMARY KEY (id);


--
-- TOC entry 4023 (class 2606 OID 19835)
-- Name: ontologies ontologies_uuid_key; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.ontologies
    ADD CONSTRAINT ontologies_uuid_key UNIQUE (uuid);


--
-- TOC entry 4033 (class 2606 OID 19870)
-- Name: ontology_entities ontology_entities_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.ontology_entities
    ADD CONSTRAINT ontology_entities_pkey PRIMARY KEY (id);


--
-- TOC entry 3932 (class 2606 OID 17895)
-- Name: ontology_mappings ontology_mappings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ontology_mappings
    ADD CONSTRAINT ontology_mappings_pkey PRIMARY KEY (id);


--
-- TOC entry 4025 (class 2606 OID 19854)
-- Name: ontology_versions ontology_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.ontology_versions
    ADD CONSTRAINT ontology_versions_pkey PRIMARY KEY (id);


--
-- TOC entry 4061 (class 2606 OID 43250)
-- Name: orchestration_decisions orchestration_decisions_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.orchestration_decisions
    ADD CONSTRAINT orchestration_decisions_pkey PRIMARY KEY (id);


--
-- TOC entry 4075 (class 2606 OID 43333)
-- Name: orchestration_feedback orchestration_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.orchestration_feedback
    ADD CONSTRAINT orchestration_feedback_pkey PRIMARY KEY (id);


--
-- TOC entry 4084 (class 2606 OID 43381)
-- Name: orchestration_overrides orchestration_overrides_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.orchestration_overrides
    ADD CONSTRAINT orchestration_overrides_pkey PRIMARY KEY (id);


--
-- TOC entry 3937 (class 2606 OID 17897)
-- Name: processing_jobs processing_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.processing_jobs
    ADD CONSTRAINT processing_jobs_pkey PRIMARY KEY (id);


--
-- TOC entry 4099 (class 2606 OID 43573)
-- Name: prov_activities prov_activities_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.prov_activities
    ADD CONSTRAINT prov_activities_pkey PRIMARY KEY (activity_id);


--
-- TOC entry 4094 (class 2606 OID 43559)
-- Name: prov_agents prov_agents_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.prov_agents
    ADD CONSTRAINT prov_agents_pkey PRIMARY KEY (agent_id);


--
-- TOC entry 4105 (class 2606 OID 43591)
-- Name: prov_entities prov_entities_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.prov_entities
    ADD CONSTRAINT prov_entities_pkey PRIMARY KEY (entity_id);


--
-- TOC entry 4110 (class 2606 OID 43619)
-- Name: prov_relationships prov_relationships_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.prov_relationships
    ADD CONSTRAINT prov_relationships_pkey PRIMARY KEY (relationship_id);


--
-- TOC entry 4127 (class 2606 OID 43700)
-- Name: provenance_activities provenance_activities_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.provenance_activities
    ADD CONSTRAINT provenance_activities_pkey PRIMARY KEY (id);


--
-- TOC entry 4129 (class 2606 OID 43702)
-- Name: provenance_activities provenance_activities_prov_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.provenance_activities
    ADD CONSTRAINT provenance_activities_prov_id_key UNIQUE (prov_id);


--
-- TOC entry 4009 (class 2606 OID 19651)
-- Name: provenance_chains provenance_chains_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.provenance_chains
    ADD CONSTRAINT provenance_chains_pkey PRIMARY KEY (id);


--
-- TOC entry 4118 (class 2606 OID 43686)
-- Name: provenance_entities provenance_entities_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.provenance_entities
    ADD CONSTRAINT provenance_entities_pkey PRIMARY KEY (id);


--
-- TOC entry 4120 (class 2606 OID 43688)
-- Name: provenance_entities provenance_entities_prov_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.provenance_entities
    ADD CONSTRAINT provenance_entities_prov_id_key UNIQUE (prov_id);


--
-- TOC entry 4019 (class 2606 OID 19824)
-- Name: search_history search_history_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.search_history
    ADD CONSTRAINT search_history_pkey PRIMARY KEY (id);


--
-- TOC entry 4000 (class 2606 OID 19601)
-- Name: semantic_drift_activities semantic_drift_activities_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.semantic_drift_activities
    ADD CONSTRAINT semantic_drift_activities_pkey PRIMARY KEY (id);


--
-- TOC entry 4005 (class 2606 OID 19632)
-- Name: term_version_anchors term_version_anchors_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.term_version_anchors
    ADD CONSTRAINT term_version_anchors_pkey PRIMARY KEY (id);


--
-- TOC entry 4007 (class 2606 OID 19634)
-- Name: term_version_anchors term_version_anchors_term_version_id_context_anchor_id_key; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.term_version_anchors
    ADD CONSTRAINT term_version_anchors_term_version_id_context_anchor_id_key UNIQUE (term_version_id, context_anchor_id);


--
-- TOC entry 3975 (class 2606 OID 19535)
-- Name: term_versions term_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.term_versions
    ADD CONSTRAINT term_versions_pkey PRIMARY KEY (id);


--
-- TOC entry 3953 (class 2606 OID 19494)
-- Name: terms terms_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.terms
    ADD CONSTRAINT terms_pkey PRIMARY KEY (id);


--
-- TOC entry 3955 (class 2606 OID 19496)
-- Name: terms terms_term_text_created_by_key; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.terms
    ADD CONSTRAINT terms_term_text_created_by_key UNIQUE (term_text, created_by);


--
-- TOC entry 3941 (class 2606 OID 17899)
-- Name: text_segments text_segments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.text_segments
    ADD CONSTRAINT text_segments_pkey PRIMARY KEY (id);


--
-- TOC entry 4066 (class 2606 OID 43292)
-- Name: tool_execution_logs tool_execution_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.tool_execution_logs
    ADD CONSTRAINT tool_execution_logs_pkey PRIMARY KEY (id);


--
-- TOC entry 4139 (class 2606 OID 49192)
-- Name: version_changelog unique_document_version_change; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.version_changelog
    ADD CONSTRAINT unique_document_version_change UNIQUE (document_id, version_number, change_type);


--
-- TOC entry 4090 (class 2606 OID 43422)
-- Name: experiment_documents_v2 unique_exp_doc; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.experiment_documents_v2
    ADD CONSTRAINT unique_exp_doc UNIQUE (experiment_id, document_id);


--
-- TOC entry 4027 (class 2606 OID 19856)
-- Name: ontology_versions uq_ontology_version; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.ontology_versions
    ADD CONSTRAINT uq_ontology_version UNIQUE (ontology_id, version_number);


--
-- TOC entry 3945 (class 2606 OID 17901)
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- TOC entry 4141 (class 2606 OID 49190)
-- Name: version_changelog version_changelog_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.version_changelog
    ADD CONSTRAINT version_changelog_pkey PRIMARY KEY (id);


--
-- TOC entry 3958 (class 1259 OID 19737)
-- Name: idx_analysis_agents_active; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_analysis_agents_active ON public.analysis_agents USING btree (is_active) WHERE (is_active = true);


--
-- TOC entry 3959 (class 1259 OID 19744)
-- Name: idx_analysis_agents_type; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_analysis_agents_type ON public.analysis_agents USING btree (agent_type);


--
-- TOC entry 3984 (class 1259 OID 19734)
-- Name: idx_context_anchors_frequency; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_context_anchors_frequency ON public.context_anchors USING btree (frequency DESC);


--
-- TOC entry 3985 (class 1259 OID 19742)
-- Name: idx_context_anchors_term; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_context_anchors_term ON public.context_anchors USING btree (anchor_term);


--
-- TOC entry 3908 (class 1259 OID 43666)
-- Name: idx_documents_experiment_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_documents_experiment_id ON public.documents USING btree (experiment_id);


--
-- TOC entry 3909 (class 1259 OID 17902)
-- Name: idx_documents_parent; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_documents_parent ON public.documents USING btree (parent_document_id);


--
-- TOC entry 3910 (class 1259 OID 43667)
-- Name: idx_documents_source_document_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_documents_source_document_id ON public.documents USING btree (source_document_id);


--
-- TOC entry 3911 (class 1259 OID 17903)
-- Name: idx_documents_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_documents_type ON public.documents USING btree (document_type);


--
-- TOC entry 3912 (class 1259 OID 43664)
-- Name: idx_documents_version_number; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_documents_version_number ON public.documents USING btree (version_number);


--
-- TOC entry 3913 (class 1259 OID 43665)
-- Name: idx_documents_version_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_documents_version_type ON public.documents USING btree (version_type);


--
-- TOC entry 3988 (class 1259 OID 19732)
-- Name: idx_drift_activities_agent; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_drift_activities_agent ON public.semantic_drift_activities USING btree (was_associated_with);


--
-- TOC entry 3989 (class 1259 OID 19731)
-- Name: idx_drift_activities_generated_entity; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_drift_activities_generated_entity ON public.semantic_drift_activities USING btree (generated_entity);


--
-- TOC entry 3990 (class 1259 OID 19741)
-- Name: idx_drift_activities_periods; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_drift_activities_periods ON public.semantic_drift_activities USING btree (start_period, end_period);


--
-- TOC entry 3991 (class 1259 OID 19733)
-- Name: idx_drift_activities_status; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_drift_activities_status ON public.semantic_drift_activities USING btree (activity_status);


--
-- TOC entry 3992 (class 1259 OID 19730)
-- Name: idx_drift_activities_used_entity; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_drift_activities_used_entity ON public.semantic_drift_activities USING btree (used_entity);


--
-- TOC entry 4036 (class 1259 OID 43158)
-- Name: idx_embeddings_document; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_embeddings_document ON public.document_embeddings USING btree (document_id);


--
-- TOC entry 4037 (class 1259 OID 43157)
-- Name: idx_embeddings_model; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_embeddings_model ON public.document_embeddings USING btree (model_name);


--
-- TOC entry 4038 (class 1259 OID 43155)
-- Name: idx_embeddings_term_period; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_embeddings_term_period ON public.document_embeddings USING btree (term, period);


--
-- TOC entry 4039 (class 1259 OID 43156)
-- Name: idx_embeddings_vector; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_embeddings_vector ON public.document_embeddings USING hnsw (embedding public.vector_cosine_ops);


--
-- TOC entry 4028 (class 1259 OID 19877)
-- Name: idx_entity_label; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_entity_label ON public.ontology_entities USING btree (label);


--
-- TOC entry 4029 (class 1259 OID 19878)
-- Name: idx_entity_type; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_entity_type ON public.ontology_entities USING btree (entity_type);


--
-- TOC entry 3917 (class 1259 OID 43410)
-- Name: idx_experiment_documents_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_experiment_documents_status ON public.experiment_documents USING btree (processing_status);


--
-- TOC entry 3918 (class 1259 OID 43411)
-- Name: idx_experiment_documents_updated; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_experiment_documents_updated ON public.experiment_documents USING btree (updated_at);


--
-- TOC entry 3921 (class 1259 OID 17904)
-- Name: idx_experiment_references_experiment; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_experiment_references_experiment ON public.experiment_references USING btree (experiment_id);


--
-- TOC entry 3922 (class 1259 OID 17905)
-- Name: idx_experiment_references_reference; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_experiment_references_reference ON public.experiment_references USING btree (reference_id);


--
-- TOC entry 3978 (class 1259 OID 19738)
-- Name: idx_fuzziness_adjustments_user; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_fuzziness_adjustments_user ON public.fuzziness_adjustments USING btree (adjusted_by);


--
-- TOC entry 3979 (class 1259 OID 19745)
-- Name: idx_fuzziness_adjustments_version; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_fuzziness_adjustments_version ON public.fuzziness_adjustments USING btree (term_version_id);


--
-- TOC entry 4076 (class 1259 OID 43368)
-- Name: idx_learning_patterns_context_type; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_learning_patterns_context_type ON public.learning_patterns USING btree (context_signature, pattern_type);


--
-- TOC entry 4077 (class 1259 OID 43369)
-- Name: idx_learning_patterns_status; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_learning_patterns_status ON public.learning_patterns USING btree (pattern_status);


--
-- TOC entry 4078 (class 1259 OID 43370)
-- Name: idx_learning_patterns_success_rate; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_learning_patterns_success_rate ON public.learning_patterns USING btree (success_rate DESC);


--
-- TOC entry 4067 (class 1259 OID 43317)
-- Name: idx_multi_model_consensus_decision; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_multi_model_consensus_decision ON public.multi_model_consensus USING btree (orchestration_decision_id);


--
-- TOC entry 4068 (class 1259 OID 43318)
-- Name: idx_multi_model_consensus_reached; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_multi_model_consensus_reached ON public.multi_model_consensus USING btree (consensus_reached);


--
-- TOC entry 4042 (class 1259 OID 43187)
-- Name: idx_oed_definitions_period; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_oed_definitions_period ON public.oed_definitions USING btree (historical_period);


--
-- TOC entry 4043 (class 1259 OID 43186)
-- Name: idx_oed_definitions_temporal; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_oed_definitions_temporal ON public.oed_definitions USING btree (first_cited_year, last_cited_year);


--
-- TOC entry 4046 (class 1259 OID 43203)
-- Name: idx_oed_historical_stats_term_period; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_oed_historical_stats_term_period ON public.oed_historical_stats USING btree (term_id, start_year, end_year);


--
-- TOC entry 4051 (class 1259 OID 43221)
-- Name: idx_oed_quotations_chronological; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_oed_quotations_chronological ON public.oed_quotation_summaries USING btree (term_id, chronological_rank);


--
-- TOC entry 4052 (class 1259 OID 43222)
-- Name: idx_oed_quotations_term_year; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_oed_quotations_term_year ON public.oed_quotation_summaries USING btree (term_id, quotation_year);


--
-- TOC entry 4030 (class 1259 OID 19876)
-- Name: idx_ontology_entity; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_ontology_entity ON public.ontology_entities USING btree (ontology_id, entity_type);


--
-- TOC entry 4055 (class 1259 OID 43280)
-- Name: idx_orchestration_decisions_agent; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_orchestration_decisions_agent ON public.orchestration_decisions USING btree (was_associated_with);


--
-- TOC entry 4056 (class 1259 OID 43279)
-- Name: idx_orchestration_decisions_document; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_orchestration_decisions_document ON public.orchestration_decisions USING btree (document_id);


--
-- TOC entry 4057 (class 1259 OID 43278)
-- Name: idx_orchestration_decisions_experiment; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_orchestration_decisions_experiment ON public.orchestration_decisions USING btree (experiment_id, created_at);


--
-- TOC entry 4058 (class 1259 OID 43276)
-- Name: idx_orchestration_decisions_status; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_orchestration_decisions_status ON public.orchestration_decisions USING btree (activity_status);


--
-- TOC entry 4059 (class 1259 OID 43277)
-- Name: idx_orchestration_decisions_term_time; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_orchestration_decisions_term_time ON public.orchestration_decisions USING btree (term_text, created_at);


--
-- TOC entry 4071 (class 1259 OID 43344)
-- Name: idx_orchestration_feedback_decision_researcher; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_orchestration_feedback_decision_researcher ON public.orchestration_feedback USING btree (orchestration_decision_id, researcher_id);


--
-- TOC entry 4072 (class 1259 OID 43346)
-- Name: idx_orchestration_feedback_provided_at; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_orchestration_feedback_provided_at ON public.orchestration_feedback USING btree (provided_at);


--
-- TOC entry 4073 (class 1259 OID 43345)
-- Name: idx_orchestration_feedback_type_status; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_orchestration_feedback_type_status ON public.orchestration_feedback USING btree (feedback_type, feedback_status);


--
-- TOC entry 4081 (class 1259 OID 43393)
-- Name: idx_orchestration_overrides_applied_at; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_orchestration_overrides_applied_at ON public.orchestration_overrides USING btree (applied_at);


--
-- TOC entry 4082 (class 1259 OID 43392)
-- Name: idx_orchestration_overrides_decision_researcher; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_orchestration_overrides_decision_researcher ON public.orchestration_overrides USING btree (orchestration_decision_id, researcher_id);


--
-- TOC entry 4134 (class 1259 OID 43798)
-- Name: idx_processing_summary_document; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_processing_summary_document ON public.document_processing_summary USING btree (document_id);


--
-- TOC entry 4135 (class 1259 OID 43799)
-- Name: idx_processing_summary_type; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_processing_summary_type ON public.document_processing_summary USING btree (processing_type);


--
-- TOC entry 4095 (class 1259 OID 43623)
-- Name: idx_prov_activities_associated; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_prov_activities_associated ON public.prov_activities USING btree (wasassociatedwith);


--
-- TOC entry 4096 (class 1259 OID 43624)
-- Name: idx_prov_activities_started; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_prov_activities_started ON public.prov_activities USING btree (startedattime);


--
-- TOC entry 4097 (class 1259 OID 43622)
-- Name: idx_prov_activities_type; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_prov_activities_type ON public.prov_activities USING btree (activity_type);


--
-- TOC entry 4091 (class 1259 OID 43621)
-- Name: idx_prov_agents_name; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_prov_agents_name ON public.prov_agents USING btree (foaf_name);


--
-- TOC entry 4092 (class 1259 OID 43620)
-- Name: idx_prov_agents_type; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_prov_agents_type ON public.prov_agents USING btree (agent_type);


--
-- TOC entry 4100 (class 1259 OID 43627)
-- Name: idx_prov_entities_attributed; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_prov_entities_attributed ON public.prov_entities USING btree (wasattributedto);


--
-- TOC entry 4101 (class 1259 OID 43628)
-- Name: idx_prov_entities_derived; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_prov_entities_derived ON public.prov_entities USING btree (wasderivedfrom);


--
-- TOC entry 4102 (class 1259 OID 43626)
-- Name: idx_prov_entities_generated; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_prov_entities_generated ON public.prov_entities USING btree (wasgeneratedby);


--
-- TOC entry 4103 (class 1259 OID 43625)
-- Name: idx_prov_entities_type; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_prov_entities_type ON public.prov_entities USING btree (entity_type);


--
-- TOC entry 4106 (class 1259 OID 43631)
-- Name: idx_prov_relationships_object; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_prov_relationships_object ON public.prov_relationships USING btree (object_id, object_type);


--
-- TOC entry 4107 (class 1259 OID 43630)
-- Name: idx_prov_relationships_subject; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_prov_relationships_subject ON public.prov_relationships USING btree (subject_id, subject_type);


--
-- TOC entry 4108 (class 1259 OID 43629)
-- Name: idx_prov_relationships_type; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_prov_relationships_type ON public.prov_relationships USING btree (relationship_type);


--
-- TOC entry 4121 (class 1259 OID 43713)
-- Name: idx_provenance_activities_activity_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_provenance_activities_activity_type ON public.provenance_activities USING btree (activity_type);


--
-- TOC entry 4122 (class 1259 OID 43712)
-- Name: idx_provenance_activities_experiment_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_provenance_activities_experiment_id ON public.provenance_activities USING btree (experiment_id);


--
-- TOC entry 4123 (class 1259 OID 43711)
-- Name: idx_provenance_activities_processing_job_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_provenance_activities_processing_job_id ON public.provenance_activities USING btree (processing_job_id);


--
-- TOC entry 4124 (class 1259 OID 43709)
-- Name: idx_provenance_activities_prov_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_provenance_activities_prov_id ON public.provenance_activities USING btree (prov_id);


--
-- TOC entry 4125 (class 1259 OID 43710)
-- Name: idx_provenance_activities_prov_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_provenance_activities_prov_type ON public.provenance_activities USING btree (prov_type);


--
-- TOC entry 4111 (class 1259 OID 43707)
-- Name: idx_provenance_entities_derived_from; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_provenance_entities_derived_from ON public.provenance_entities USING btree (derived_from_entity);


--
-- TOC entry 4112 (class 1259 OID 43705)
-- Name: idx_provenance_entities_document_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_provenance_entities_document_id ON public.provenance_entities USING btree (document_id);


--
-- TOC entry 4113 (class 1259 OID 43706)
-- Name: idx_provenance_entities_experiment_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_provenance_entities_experiment_id ON public.provenance_entities USING btree (experiment_id);


--
-- TOC entry 4114 (class 1259 OID 43708)
-- Name: idx_provenance_entities_generated_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_provenance_entities_generated_by ON public.provenance_entities USING btree (generated_by_activity);


--
-- TOC entry 4115 (class 1259 OID 43703)
-- Name: idx_provenance_entities_prov_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_provenance_entities_prov_id ON public.provenance_entities USING btree (prov_id);


--
-- TOC entry 4116 (class 1259 OID 43704)
-- Name: idx_provenance_entities_prov_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_provenance_entities_prov_type ON public.provenance_entities USING btree (prov_type);


--
-- TOC entry 4001 (class 1259 OID 19735)
-- Name: idx_term_version_anchors_anchor; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_term_version_anchors_anchor ON public.term_version_anchors USING btree (context_anchor_id);


--
-- TOC entry 4002 (class 1259 OID 19736)
-- Name: idx_term_version_anchors_similarity; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_term_version_anchors_similarity ON public.term_version_anchors USING btree (similarity_score DESC);


--
-- TOC entry 4003 (class 1259 OID 19743)
-- Name: idx_term_version_anchors_version; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_term_version_anchors_version ON public.term_version_anchors USING btree (term_version_id);


--
-- TOC entry 3962 (class 1259 OID 19729)
-- Name: idx_term_versions_corpus; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_term_versions_corpus ON public.term_versions USING btree (corpus_source);


--
-- TOC entry 3963 (class 1259 OID 19727)
-- Name: idx_term_versions_current; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_term_versions_current ON public.term_versions USING btree (is_current) WHERE (is_current = true);


--
-- TOC entry 3964 (class 1259 OID 19728)
-- Name: idx_term_versions_fuzziness; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_term_versions_fuzziness ON public.term_versions USING btree (fuzziness_score);


--
-- TOC entry 3965 (class 1259 OID 19725)
-- Name: idx_term_versions_temporal_period; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_term_versions_temporal_period ON public.term_versions USING btree (temporal_period);


--
-- TOC entry 3966 (class 1259 OID 19726)
-- Name: idx_term_versions_temporal_years; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_term_versions_temporal_years ON public.term_versions USING btree (temporal_start_year, temporal_end_year);


--
-- TOC entry 3967 (class 1259 OID 19740)
-- Name: idx_term_versions_term_id; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_term_versions_term_id ON public.term_versions USING btree (term_id);


--
-- TOC entry 3946 (class 1259 OID 19723)
-- Name: idx_terms_created_by; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_terms_created_by ON public.terms USING btree (created_by);


--
-- TOC entry 3947 (class 1259 OID 19724)
-- Name: idx_terms_research_domain; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_terms_research_domain ON public.terms USING btree (research_domain);


--
-- TOC entry 3948 (class 1259 OID 19722)
-- Name: idx_terms_status; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_terms_status ON public.terms USING btree (status);


--
-- TOC entry 3949 (class 1259 OID 19739)
-- Name: idx_terms_text; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_terms_text ON public.terms USING btree (term_text);


--
-- TOC entry 4062 (class 1259 OID 43298)
-- Name: idx_tool_execution_logs_decision_order; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_tool_execution_logs_decision_order ON public.tool_execution_logs USING btree (orchestration_decision_id, execution_order);


--
-- TOC entry 4063 (class 1259 OID 43300)
-- Name: idx_tool_execution_logs_status; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_tool_execution_logs_status ON public.tool_execution_logs USING btree (execution_status);


--
-- TOC entry 4064 (class 1259 OID 43299)
-- Name: idx_tool_execution_logs_tool_name; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_tool_execution_logs_tool_name ON public.tool_execution_logs USING btree (tool_name);


--
-- TOC entry 4136 (class 1259 OID 49204)
-- Name: idx_version_changelog_change_type; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_version_changelog_change_type ON public.version_changelog USING btree (change_type);


--
-- TOC entry 4137 (class 1259 OID 49203)
-- Name: idx_version_changelog_document_version; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_version_changelog_document_version ON public.version_changelog USING btree (document_id, version_number);


--
-- TOC entry 3960 (class 1259 OID 19522)
-- Name: ix_analysis_agents_agent_type; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_analysis_agents_agent_type ON public.analysis_agents USING btree (agent_type);


--
-- TOC entry 3961 (class 1259 OID 19523)
-- Name: ix_analysis_agents_is_active; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_analysis_agents_is_active ON public.analysis_agents USING btree (is_active);


--
-- TOC entry 3986 (class 1259 OID 19592)
-- Name: ix_context_anchors_anchor_term; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE UNIQUE INDEX ix_context_anchors_anchor_term ON public.context_anchors USING btree (anchor_term);


--
-- TOC entry 3987 (class 1259 OID 19591)
-- Name: ix_context_anchors_frequency; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_context_anchors_frequency ON public.context_anchors USING btree (frequency);


--
-- TOC entry 3914 (class 1259 OID 17906)
-- Name: ix_documents_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_documents_user_id ON public.documents USING btree (user_id);


--
-- TOC entry 4031 (class 1259 OID 19879)
-- Name: ix_entity_embedding_vector; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_entity_embedding_vector ON public.ontology_entities USING ivfflat (embedding public.vector_cosine_ops) WITH (lists='100');


--
-- TOC entry 4087 (class 1259 OID 43433)
-- Name: ix_experiment_documents_v2_document_id; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_experiment_documents_v2_document_id ON public.experiment_documents_v2 USING btree (document_id);


--
-- TOC entry 4088 (class 1259 OID 43434)
-- Name: ix_experiment_documents_v2_experiment_id; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_experiment_documents_v2_experiment_id ON public.experiment_documents_v2 USING btree (experiment_id);


--
-- TOC entry 3925 (class 1259 OID 17907)
-- Name: ix_experiments_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_experiments_user_id ON public.experiments USING btree (user_id);


--
-- TOC entry 3928 (class 1259 OID 17908)
-- Name: ix_extracted_entities_processing_job_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_extracted_entities_processing_job_id ON public.extracted_entities USING btree (processing_job_id);


--
-- TOC entry 3929 (class 1259 OID 17909)
-- Name: ix_extracted_entities_text_segment_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_extracted_entities_text_segment_id ON public.extracted_entities USING btree (text_segment_id);


--
-- TOC entry 3980 (class 1259 OID 19575)
-- Name: ix_fuzziness_adjustments_adjusted_by; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_fuzziness_adjustments_adjusted_by ON public.fuzziness_adjustments USING btree (adjusted_by);


--
-- TOC entry 3981 (class 1259 OID 19574)
-- Name: ix_fuzziness_adjustments_term_version_id; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_fuzziness_adjustments_term_version_id ON public.fuzziness_adjustments USING btree (term_version_id);


--
-- TOC entry 3930 (class 1259 OID 17910)
-- Name: ix_ontology_mappings_extracted_entity_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ontology_mappings_extracted_entity_id ON public.ontology_mappings USING btree (extracted_entity_id);


--
-- TOC entry 3933 (class 1259 OID 17911)
-- Name: ix_processing_jobs_document_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_processing_jobs_document_id ON public.processing_jobs USING btree (document_id);


--
-- TOC entry 3934 (class 1259 OID 17912)
-- Name: ix_processing_jobs_parent_job_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_processing_jobs_parent_job_id ON public.processing_jobs USING btree (parent_job_id);


--
-- TOC entry 3935 (class 1259 OID 17913)
-- Name: ix_processing_jobs_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_processing_jobs_user_id ON public.processing_jobs USING btree (user_id);


--
-- TOC entry 3993 (class 1259 OID 19625)
-- Name: ix_semantic_drift_activities_activity_status; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_semantic_drift_activities_activity_status ON public.semantic_drift_activities USING btree (activity_status);


--
-- TOC entry 3994 (class 1259 OID 19626)
-- Name: ix_semantic_drift_activities_end_period; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_semantic_drift_activities_end_period ON public.semantic_drift_activities USING btree (end_period);


--
-- TOC entry 3995 (class 1259 OID 19627)
-- Name: ix_semantic_drift_activities_generated_entity; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_semantic_drift_activities_generated_entity ON public.semantic_drift_activities USING btree (generated_entity);


--
-- TOC entry 3996 (class 1259 OID 19623)
-- Name: ix_semantic_drift_activities_start_period; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_semantic_drift_activities_start_period ON public.semantic_drift_activities USING btree (start_period);


--
-- TOC entry 3997 (class 1259 OID 19622)
-- Name: ix_semantic_drift_activities_used_entity; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_semantic_drift_activities_used_entity ON public.semantic_drift_activities USING btree (used_entity);


--
-- TOC entry 3998 (class 1259 OID 19624)
-- Name: ix_semantic_drift_activities_was_associated_with; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_semantic_drift_activities_was_associated_with ON public.semantic_drift_activities USING btree (was_associated_with);


--
-- TOC entry 3968 (class 1259 OID 19553)
-- Name: ix_term_versions_corpus_source; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_term_versions_corpus_source ON public.term_versions USING btree (corpus_source);


--
-- TOC entry 3969 (class 1259 OID 19555)
-- Name: ix_term_versions_is_current; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_term_versions_is_current ON public.term_versions USING btree (is_current);


--
-- TOC entry 3970 (class 1259 OID 19554)
-- Name: ix_term_versions_temporal_end_year; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_term_versions_temporal_end_year ON public.term_versions USING btree (temporal_end_year);


--
-- TOC entry 3971 (class 1259 OID 19556)
-- Name: ix_term_versions_temporal_period; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_term_versions_temporal_period ON public.term_versions USING btree (temporal_period);


--
-- TOC entry 3972 (class 1259 OID 19552)
-- Name: ix_term_versions_temporal_start_year; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_term_versions_temporal_start_year ON public.term_versions USING btree (temporal_start_year);


--
-- TOC entry 3973 (class 1259 OID 19551)
-- Name: ix_term_versions_term_id; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_term_versions_term_id ON public.term_versions USING btree (term_id);


--
-- TOC entry 3950 (class 1259 OID 19508)
-- Name: ix_terms_created_by; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_terms_created_by ON public.terms USING btree (created_by);


--
-- TOC entry 3951 (class 1259 OID 19507)
-- Name: ix_terms_research_domain; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_terms_research_domain ON public.terms USING btree (research_domain);


--
-- TOC entry 3938 (class 1259 OID 17914)
-- Name: ix_text_segments_document_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_text_segments_document_id ON public.text_segments USING btree (document_id);


--
-- TOC entry 3939 (class 1259 OID 17915)
-- Name: ix_text_segments_parent_segment_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_text_segments_parent_segment_id ON public.text_segments USING btree (parent_segment_id);


--
-- TOC entry 3942 (class 1259 OID 17916)
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- TOC entry 3943 (class 1259 OID 17917)
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_username ON public.users USING btree (username);


--
-- TOC entry 4214 (class 2620 OID 19749)
-- Name: term_version_anchors trigger_update_context_anchor_frequency; Type: TRIGGER; Schema: public; Owner: ontextract_user
--

CREATE TRIGGER trigger_update_context_anchor_frequency AFTER INSERT OR DELETE ON public.term_version_anchors FOR EACH ROW EXECUTE FUNCTION public.update_context_anchor_frequency();


--
-- TOC entry 4213 (class 2620 OID 19747)
-- Name: terms trigger_update_terms_updated_at; Type: TRIGGER; Schema: public; Owner: ontextract_user
--

CREATE TRIGGER trigger_update_terms_updated_at BEFORE UPDATE ON public.terms FOR EACH ROW EXECUTE FUNCTION public.update_terms_updated_at();


--
-- TOC entry 4216 (class 2620 OID 43735)
-- Name: provenance_activities update_provenance_activities_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_provenance_activities_updated_at BEFORE UPDATE ON public.provenance_activities FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- TOC entry 4215 (class 2620 OID 43734)
-- Name: provenance_entities update_provenance_entities_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_provenance_entities_updated_at BEFORE UPDATE ON public.provenance_entities FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- TOC entry 4161 (class 2606 OID 19517)
-- Name: analysis_agents analysis_agents_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.analysis_agents
    ADD CONSTRAINT analysis_agents_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- TOC entry 4167 (class 2606 OID 19581)
-- Name: context_anchors context_anchors_first_used_in_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.context_anchors
    ADD CONSTRAINT context_anchors_first_used_in_fkey FOREIGN KEY (first_used_in) REFERENCES public.term_versions(id);


--
-- TOC entry 4168 (class 2606 OID 19586)
-- Name: context_anchors context_anchors_last_used_in_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.context_anchors
    ADD CONSTRAINT context_anchors_last_used_in_fkey FOREIGN KEY (last_used_in) REFERENCES public.term_versions(id);


--
-- TOC entry 4180 (class 2606 OID 43150)
-- Name: document_embeddings document_embeddings_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.document_embeddings
    ADD CONSTRAINT document_embeddings_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id);


--
-- TOC entry 4208 (class 2606 OID 43783)
-- Name: document_processing_summary document_processing_summary_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.document_processing_summary
    ADD CONSTRAINT document_processing_summary_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- TOC entry 4209 (class 2606 OID 43793)
-- Name: document_processing_summary document_processing_summary_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.document_processing_summary
    ADD CONSTRAINT document_processing_summary_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.processing_jobs(id);


--
-- TOC entry 4210 (class 2606 OID 43788)
-- Name: document_processing_summary document_processing_summary_source_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.document_processing_summary
    ADD CONSTRAINT document_processing_summary_source_document_id_fkey FOREIGN KEY (source_document_id) REFERENCES public.documents(id);


--
-- TOC entry 4142 (class 2606 OID 17918)
-- Name: documents documents_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- TOC entry 4146 (class 2606 OID 17923)
-- Name: experiment_documents experiment_documents_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.experiment_documents
    ADD CONSTRAINT experiment_documents_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id);


--
-- TOC entry 4147 (class 2606 OID 17928)
-- Name: experiment_documents experiment_documents_experiment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.experiment_documents
    ADD CONSTRAINT experiment_documents_experiment_id_fkey FOREIGN KEY (experiment_id) REFERENCES public.experiments(id);


--
-- TOC entry 4198 (class 2606 OID 43428)
-- Name: experiment_documents_v2 experiment_documents_v2_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.experiment_documents_v2
    ADD CONSTRAINT experiment_documents_v2_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id);


--
-- TOC entry 4199 (class 2606 OID 43423)
-- Name: experiment_documents_v2 experiment_documents_v2_experiment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.experiment_documents_v2
    ADD CONSTRAINT experiment_documents_v2_experiment_id_fkey FOREIGN KEY (experiment_id) REFERENCES public.experiments(id);


--
-- TOC entry 4148 (class 2606 OID 17933)
-- Name: experiment_references experiment_references_experiment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.experiment_references
    ADD CONSTRAINT experiment_references_experiment_id_fkey FOREIGN KEY (experiment_id) REFERENCES public.experiments(id);


--
-- TOC entry 4149 (class 2606 OID 17938)
-- Name: experiment_references experiment_references_reference_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.experiment_references
    ADD CONSTRAINT experiment_references_reference_id_fkey FOREIGN KEY (reference_id) REFERENCES public.documents(id);


--
-- TOC entry 4150 (class 2606 OID 17943)
-- Name: experiments experiments_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.experiments
    ADD CONSTRAINT experiments_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- TOC entry 4151 (class 2606 OID 17948)
-- Name: extracted_entities extracted_entities_processing_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.extracted_entities
    ADD CONSTRAINT extracted_entities_processing_job_id_fkey FOREIGN KEY (processing_job_id) REFERENCES public.processing_jobs(id);


--
-- TOC entry 4152 (class 2606 OID 17953)
-- Name: extracted_entities extracted_entities_text_segment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.extracted_entities
    ADD CONSTRAINT extracted_entities_text_segment_id_fkey FOREIGN KEY (text_segment_id) REFERENCES public.text_segments(id);


--
-- TOC entry 4143 (class 2606 OID 43654)
-- Name: documents fk_documents_experiment; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT fk_documents_experiment FOREIGN KEY (experiment_id) REFERENCES public.experiments(id) ON DELETE SET NULL;


--
-- TOC entry 4144 (class 2606 OID 17958)
-- Name: documents fk_documents_parent_document_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT fk_documents_parent_document_id FOREIGN KEY (parent_document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- TOC entry 4145 (class 2606 OID 43659)
-- Name: documents fk_documents_source; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT fk_documents_source FOREIGN KEY (source_document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- TOC entry 4206 (class 2606 OID 43729)
-- Name: provenance_activities fk_provenance_activities_experiment; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.provenance_activities
    ADD CONSTRAINT fk_provenance_activities_experiment FOREIGN KEY (experiment_id) REFERENCES public.experiments(id) ON DELETE SET NULL;


--
-- TOC entry 4207 (class 2606 OID 43724)
-- Name: provenance_activities fk_provenance_activities_processing_job; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.provenance_activities
    ADD CONSTRAINT fk_provenance_activities_processing_job FOREIGN KEY (processing_job_id) REFERENCES public.processing_jobs(id) ON DELETE CASCADE;


--
-- TOC entry 4204 (class 2606 OID 43714)
-- Name: provenance_entities fk_provenance_entities_document; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.provenance_entities
    ADD CONSTRAINT fk_provenance_entities_document FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- TOC entry 4205 (class 2606 OID 43719)
-- Name: provenance_entities fk_provenance_entities_experiment; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.provenance_entities
    ADD CONSTRAINT fk_provenance_entities_experiment FOREIGN KEY (experiment_id) REFERENCES public.experiments(id) ON DELETE SET NULL;


--
-- TOC entry 4165 (class 2606 OID 19569)
-- Name: fuzziness_adjustments fuzziness_adjustments_adjusted_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.fuzziness_adjustments
    ADD CONSTRAINT fuzziness_adjustments_adjusted_by_fkey FOREIGN KEY (adjusted_by) REFERENCES public.users(id);


--
-- TOC entry 4166 (class 2606 OID 19564)
-- Name: fuzziness_adjustments fuzziness_adjustments_term_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.fuzziness_adjustments
    ADD CONSTRAINT fuzziness_adjustments_term_version_id_fkey FOREIGN KEY (term_version_id) REFERENCES public.term_versions(id);


--
-- TOC entry 4195 (class 2606 OID 43363)
-- Name: learning_patterns learning_patterns_derived_from_feedback_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.learning_patterns
    ADD CONSTRAINT learning_patterns_derived_from_feedback_fkey FOREIGN KEY (derived_from_feedback) REFERENCES public.orchestration_feedback(id);


--
-- TOC entry 4192 (class 2606 OID 43312)
-- Name: multi_model_consensus multi_model_consensus_orchestration_decision_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.multi_model_consensus
    ADD CONSTRAINT multi_model_consensus_orchestration_decision_id_fkey FOREIGN KEY (orchestration_decision_id) REFERENCES public.orchestration_decisions(id) ON DELETE CASCADE;


--
-- TOC entry 4182 (class 2606 OID 43181)
-- Name: oed_definitions oed_definitions_term_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.oed_definitions
    ADD CONSTRAINT oed_definitions_term_id_fkey FOREIGN KEY (term_id) REFERENCES public.terms(id) ON DELETE CASCADE;


--
-- TOC entry 4181 (class 2606 OID 43167)
-- Name: oed_etymology oed_etymology_term_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.oed_etymology
    ADD CONSTRAINT oed_etymology_term_id_fkey FOREIGN KEY (term_id) REFERENCES public.terms(id) ON DELETE CASCADE;


--
-- TOC entry 4183 (class 2606 OID 43198)
-- Name: oed_historical_stats oed_historical_stats_term_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.oed_historical_stats
    ADD CONSTRAINT oed_historical_stats_term_id_fkey FOREIGN KEY (term_id) REFERENCES public.terms(id) ON DELETE CASCADE;


--
-- TOC entry 4184 (class 2606 OID 43216)
-- Name: oed_quotation_summaries oed_quotation_summaries_oed_definition_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.oed_quotation_summaries
    ADD CONSTRAINT oed_quotation_summaries_oed_definition_id_fkey FOREIGN KEY (oed_definition_id) REFERENCES public.oed_definitions(id) ON DELETE CASCADE;


--
-- TOC entry 4185 (class 2606 OID 43211)
-- Name: oed_quotation_summaries oed_quotation_summaries_term_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.oed_quotation_summaries
    ADD CONSTRAINT oed_quotation_summaries_term_id_fkey FOREIGN KEY (term_id) REFERENCES public.terms(id) ON DELETE CASCADE;


--
-- TOC entry 4176 (class 2606 OID 19836)
-- Name: ontologies ontologies_domain_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.ontologies
    ADD CONSTRAINT ontologies_domain_id_fkey FOREIGN KEY (domain_id) REFERENCES public.domains(id);


--
-- TOC entry 4177 (class 2606 OID 19841)
-- Name: ontologies ontologies_parent_ontology_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.ontologies
    ADD CONSTRAINT ontologies_parent_ontology_id_fkey FOREIGN KEY (parent_ontology_id) REFERENCES public.ontologies(id);


--
-- TOC entry 4179 (class 2606 OID 19871)
-- Name: ontology_entities ontology_entities_ontology_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.ontology_entities
    ADD CONSTRAINT ontology_entities_ontology_id_fkey FOREIGN KEY (ontology_id) REFERENCES public.ontologies(id);


--
-- TOC entry 4153 (class 2606 OID 17963)
-- Name: ontology_mappings ontology_mappings_extracted_entity_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ontology_mappings
    ADD CONSTRAINT ontology_mappings_extracted_entity_id_fkey FOREIGN KEY (extracted_entity_id) REFERENCES public.extracted_entities(id);


--
-- TOC entry 4178 (class 2606 OID 19857)
-- Name: ontology_versions ontology_versions_ontology_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.ontology_versions
    ADD CONSTRAINT ontology_versions_ontology_id_fkey FOREIGN KEY (ontology_id) REFERENCES public.ontologies(id);


--
-- TOC entry 4186 (class 2606 OID 43271)
-- Name: orchestration_decisions orchestration_decisions_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.orchestration_decisions
    ADD CONSTRAINT orchestration_decisions_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- TOC entry 4187 (class 2606 OID 43251)
-- Name: orchestration_decisions orchestration_decisions_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.orchestration_decisions
    ADD CONSTRAINT orchestration_decisions_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id);


--
-- TOC entry 4188 (class 2606 OID 43256)
-- Name: orchestration_decisions orchestration_decisions_experiment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.orchestration_decisions
    ADD CONSTRAINT orchestration_decisions_experiment_id_fkey FOREIGN KEY (experiment_id) REFERENCES public.experiments(id);


--
-- TOC entry 4189 (class 2606 OID 43266)
-- Name: orchestration_decisions orchestration_decisions_used_entity_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.orchestration_decisions
    ADD CONSTRAINT orchestration_decisions_used_entity_fkey FOREIGN KEY (used_entity) REFERENCES public.term_versions(id);


--
-- TOC entry 4190 (class 2606 OID 43261)
-- Name: orchestration_decisions orchestration_decisions_was_associated_with_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.orchestration_decisions
    ADD CONSTRAINT orchestration_decisions_was_associated_with_fkey FOREIGN KEY (was_associated_with) REFERENCES public.analysis_agents(id);


--
-- TOC entry 4193 (class 2606 OID 43334)
-- Name: orchestration_feedback orchestration_feedback_orchestration_decision_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.orchestration_feedback
    ADD CONSTRAINT orchestration_feedback_orchestration_decision_id_fkey FOREIGN KEY (orchestration_decision_id) REFERENCES public.orchestration_decisions(id) ON DELETE CASCADE;


--
-- TOC entry 4194 (class 2606 OID 43339)
-- Name: orchestration_feedback orchestration_feedback_researcher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.orchestration_feedback
    ADD CONSTRAINT orchestration_feedback_researcher_id_fkey FOREIGN KEY (researcher_id) REFERENCES public.users(id);


--
-- TOC entry 4196 (class 2606 OID 43382)
-- Name: orchestration_overrides orchestration_overrides_orchestration_decision_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.orchestration_overrides
    ADD CONSTRAINT orchestration_overrides_orchestration_decision_id_fkey FOREIGN KEY (orchestration_decision_id) REFERENCES public.orchestration_decisions(id) ON DELETE CASCADE;


--
-- TOC entry 4197 (class 2606 OID 43387)
-- Name: orchestration_overrides orchestration_overrides_researcher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.orchestration_overrides
    ADD CONSTRAINT orchestration_overrides_researcher_id_fkey FOREIGN KEY (researcher_id) REFERENCES public.users(id);


--
-- TOC entry 4154 (class 2606 OID 17968)
-- Name: processing_jobs processing_jobs_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.processing_jobs
    ADD CONSTRAINT processing_jobs_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id);


--
-- TOC entry 4155 (class 2606 OID 17973)
-- Name: processing_jobs processing_jobs_parent_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.processing_jobs
    ADD CONSTRAINT processing_jobs_parent_job_id_fkey FOREIGN KEY (parent_job_id) REFERENCES public.processing_jobs(id);


--
-- TOC entry 4156 (class 2606 OID 17978)
-- Name: processing_jobs processing_jobs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.processing_jobs
    ADD CONSTRAINT processing_jobs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- TOC entry 4200 (class 2606 OID 43574)
-- Name: prov_activities prov_activities_wasassociatedwith_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.prov_activities
    ADD CONSTRAINT prov_activities_wasassociatedwith_fkey FOREIGN KEY (wasassociatedwith) REFERENCES public.prov_agents(agent_id);


--
-- TOC entry 4201 (class 2606 OID 43597)
-- Name: prov_entities prov_entities_wasattributedto_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.prov_entities
    ADD CONSTRAINT prov_entities_wasattributedto_fkey FOREIGN KEY (wasattributedto) REFERENCES public.prov_agents(agent_id);


--
-- TOC entry 4202 (class 2606 OID 43602)
-- Name: prov_entities prov_entities_wasderivedfrom_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.prov_entities
    ADD CONSTRAINT prov_entities_wasderivedfrom_fkey FOREIGN KEY (wasderivedfrom) REFERENCES public.prov_entities(entity_id);


--
-- TOC entry 4203 (class 2606 OID 43592)
-- Name: prov_entities prov_entities_wasgeneratedby_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.prov_entities
    ADD CONSTRAINT prov_entities_wasgeneratedby_fkey FOREIGN KEY (wasgeneratedby) REFERENCES public.prov_activities(activity_id);


--
-- TOC entry 4175 (class 2606 OID 19652)
-- Name: provenance_chains provenance_chains_derivation_activity_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.provenance_chains
    ADD CONSTRAINT provenance_chains_derivation_activity_fkey FOREIGN KEY (derivation_activity) REFERENCES public.semantic_drift_activities(id);


--
-- TOC entry 4169 (class 2606 OID 19617)
-- Name: semantic_drift_activities semantic_drift_activities_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.semantic_drift_activities
    ADD CONSTRAINT semantic_drift_activities_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- TOC entry 4170 (class 2606 OID 19607)
-- Name: semantic_drift_activities semantic_drift_activities_generated_entity_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.semantic_drift_activities
    ADD CONSTRAINT semantic_drift_activities_generated_entity_fkey FOREIGN KEY (generated_entity) REFERENCES public.term_versions(id);


--
-- TOC entry 4171 (class 2606 OID 19602)
-- Name: semantic_drift_activities semantic_drift_activities_used_entity_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.semantic_drift_activities
    ADD CONSTRAINT semantic_drift_activities_used_entity_fkey FOREIGN KEY (used_entity) REFERENCES public.term_versions(id);


--
-- TOC entry 4172 (class 2606 OID 19612)
-- Name: semantic_drift_activities semantic_drift_activities_was_associated_with_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.semantic_drift_activities
    ADD CONSTRAINT semantic_drift_activities_was_associated_with_fkey FOREIGN KEY (was_associated_with) REFERENCES public.analysis_agents(id);


--
-- TOC entry 4173 (class 2606 OID 19640)
-- Name: term_version_anchors term_version_anchors_context_anchor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.term_version_anchors
    ADD CONSTRAINT term_version_anchors_context_anchor_id_fkey FOREIGN KEY (context_anchor_id) REFERENCES public.context_anchors(id);


--
-- TOC entry 4174 (class 2606 OID 19635)
-- Name: term_version_anchors term_version_anchors_term_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.term_version_anchors
    ADD CONSTRAINT term_version_anchors_term_version_id_fkey FOREIGN KEY (term_version_id) REFERENCES public.term_versions(id);


--
-- TOC entry 4162 (class 2606 OID 19546)
-- Name: term_versions term_versions_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.term_versions
    ADD CONSTRAINT term_versions_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- TOC entry 4163 (class 2606 OID 19536)
-- Name: term_versions term_versions_term_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.term_versions
    ADD CONSTRAINT term_versions_term_id_fkey FOREIGN KEY (term_id) REFERENCES public.terms(id);


--
-- TOC entry 4164 (class 2606 OID 19541)
-- Name: term_versions term_versions_was_derived_from_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.term_versions
    ADD CONSTRAINT term_versions_was_derived_from_fkey FOREIGN KEY (was_derived_from) REFERENCES public.term_versions(id);


--
-- TOC entry 4159 (class 2606 OID 19497)
-- Name: terms terms_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.terms
    ADD CONSTRAINT terms_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- TOC entry 4160 (class 2606 OID 19502)
-- Name: terms terms_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.terms
    ADD CONSTRAINT terms_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public.users(id);


--
-- TOC entry 4157 (class 2606 OID 17983)
-- Name: text_segments text_segments_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.text_segments
    ADD CONSTRAINT text_segments_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id);


--
-- TOC entry 4158 (class 2606 OID 17988)
-- Name: text_segments text_segments_parent_segment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.text_segments
    ADD CONSTRAINT text_segments_parent_segment_id_fkey FOREIGN KEY (parent_segment_id) REFERENCES public.text_segments(id);


--
-- TOC entry 4191 (class 2606 OID 43293)
-- Name: tool_execution_logs tool_execution_logs_orchestration_decision_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.tool_execution_logs
    ADD CONSTRAINT tool_execution_logs_orchestration_decision_id_fkey FOREIGN KEY (orchestration_decision_id) REFERENCES public.orchestration_decisions(id) ON DELETE CASCADE;


--
-- TOC entry 4211 (class 2606 OID 49198)
-- Name: version_changelog version_changelog_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.version_changelog
    ADD CONSTRAINT version_changelog_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- TOC entry 4212 (class 2606 OID 49193)
-- Name: version_changelog version_changelog_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.version_changelog
    ADD CONSTRAINT version_changelog_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- TOC entry 4430 (class 0 OID 0)
-- Dependencies: 9
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT ALL ON SCHEMA public TO ontextract_user;


--
-- TOC entry 4444 (class 0 OID 0)
-- Dependencies: 221
-- Name: TABLE documents; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.documents TO ontextract_user;


--
-- TOC entry 4445 (class 0 OID 0)
-- Dependencies: 225
-- Name: TABLE experiments; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.experiments TO ontextract_user;


--
-- TOC entry 4446 (class 0 OID 0)
-- Dependencies: 273
-- Name: TABLE document_version_chains; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.document_version_chains TO ontextract_user;


--
-- TOC entry 4447 (class 0 OID 0)
-- Dependencies: 233
-- Name: TABLE text_segments; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.text_segments TO ontextract_user;


--
-- TOC entry 4449 (class 0 OID 0)
-- Dependencies: 222
-- Name: SEQUENCE documents_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.documents_id_seq TO ontextract_user;


--
-- TOC entry 4459 (class 0 OID 0)
-- Dependencies: 223
-- Name: TABLE experiment_documents; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.experiment_documents TO ontextract_user;


--
-- TOC entry 4461 (class 0 OID 0)
-- Dependencies: 224
-- Name: TABLE experiment_references; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.experiment_references TO ontextract_user;


--
-- TOC entry 4463 (class 0 OID 0)
-- Dependencies: 226
-- Name: SEQUENCE experiments_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.experiments_id_seq TO ontextract_user;


--
-- TOC entry 4464 (class 0 OID 0)
-- Dependencies: 227
-- Name: TABLE extracted_entities; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.extracted_entities TO ontextract_user;


--
-- TOC entry 4466 (class 0 OID 0)
-- Dependencies: 228
-- Name: SEQUENCE extracted_entities_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.extracted_entities_id_seq TO ontextract_user;


--
-- TOC entry 4475 (class 0 OID 0)
-- Dependencies: 229
-- Name: TABLE ontology_mappings; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.ontology_mappings TO ontextract_user;


--
-- TOC entry 4477 (class 0 OID 0)
-- Dependencies: 230
-- Name: SEQUENCE ontology_mappings_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.ontology_mappings_id_seq TO ontextract_user;


--
-- TOC entry 4487 (class 0 OID 0)
-- Dependencies: 231
-- Name: TABLE processing_jobs; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.processing_jobs TO ontextract_user;


--
-- TOC entry 4489 (class 0 OID 0)
-- Dependencies: 232
-- Name: SEQUENCE processing_jobs_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.processing_jobs_id_seq TO ontextract_user;


--
-- TOC entry 4495 (class 0 OID 0)
-- Dependencies: 277
-- Name: TABLE provenance_activities; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.provenance_activities TO ontextract_user;


--
-- TOC entry 4497 (class 0 OID 0)
-- Dependencies: 276
-- Name: SEQUENCE provenance_activities_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.provenance_activities_id_seq TO ontextract_user;


--
-- TOC entry 4503 (class 0 OID 0)
-- Dependencies: 275
-- Name: TABLE provenance_entities; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.provenance_entities TO ontextract_user;


--
-- TOC entry 4505 (class 0 OID 0)
-- Dependencies: 274
-- Name: SEQUENCE provenance_entities_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.provenance_entities_id_seq TO ontextract_user;


--
-- TOC entry 4509 (class 0 OID 0)
-- Dependencies: 234
-- Name: SEQUENCE text_segments_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.text_segments_id_seq TO ontextract_user;


--
-- TOC entry 4513 (class 0 OID 0)
-- Dependencies: 235
-- Name: TABLE users; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.users TO ontextract_user;


--
-- TOC entry 4515 (class 0 OID 0)
-- Dependencies: 236
-- Name: SEQUENCE users_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.users_id_seq TO ontextract_user;


--
-- TOC entry 2551 (class 826 OID 43402)
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO ontextract_user;


--
-- TOC entry 2550 (class 826 OID 43401)
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES TO ontextract_user;


-- Completed on 2025-09-07 20:11:58 EDT

--
-- PostgreSQL database dump complete
--

\unrestrict EUoSdvmUces6acmYtXfddHB3ZRkpC8zOdYrcArwV0TNe7XCSxtvdOdVkhHwo3UO

