--
-- PostgreSQL database dump
--

\restrict wuwkqIWPiWStDe9iqczqagv4EF0JEFc2bcobT6yo7XohxM0QhBWc7DeEKivL0Bo

-- Dumped from database version 17.6 (Ubuntu 17.6-1.pgdg24.04+1)
-- Dumped by pg_dump version 17.6 (Ubuntu 17.6-1.pgdg24.04+1)

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
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


--
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

SET default_tablespace = '';

SET default_table_access_method = heap;

--
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
-- Name: document_embeddings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ontextract_user
--

ALTER SEQUENCE public.document_embeddings_id_seq OWNED BY public.document_embeddings.id;


--
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
    parent_document_id integer
);


ALTER TABLE public.documents OWNER TO postgres;

--
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
-- Name: documents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.documents_id_seq OWNED BY public.documents.id;


--
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
-- Name: domains_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ontextract_user
--

ALTER SEQUENCE public.domains_id_seq OWNED BY public.domains.id;


--
-- Name: experiment_documents; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.experiment_documents (
    experiment_id integer NOT NULL,
    document_id integer NOT NULL,
    added_at timestamp without time zone
);


ALTER TABLE public.experiment_documents OWNER TO postgres;

--
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
-- Name: experiments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.experiments_id_seq OWNED BY public.experiments.id;


--
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
-- Name: extracted_entities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.extracted_entities_id_seq OWNED BY public.extracted_entities.id;


--
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
-- Name: ontologies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ontextract_user
--

ALTER SEQUENCE public.ontologies_id_seq OWNED BY public.ontologies.id;


--
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
-- Name: ontology_entities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ontextract_user
--

ALTER SEQUENCE public.ontology_entities_id_seq OWNED BY public.ontology_entities.id;


--
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
-- Name: ontology_mappings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ontology_mappings_id_seq OWNED BY public.ontology_mappings.id;


--
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
-- Name: ontology_versions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ontextract_user
--

ALTER SEQUENCE public.ontology_versions_id_seq OWNED BY public.ontology_versions.id;


--
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
-- Name: processing_jobs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.processing_jobs_id_seq OWNED BY public.processing_jobs.id;


--
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
-- Name: search_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ontextract_user
--

ALTER SEQUENCE public.search_history_id_seq OWNED BY public.search_history.id;


--
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
-- Name: COLUMN term_versions.source_citation; Type: COMMENT; Schema: public; Owner: ontextract_user
--

COMMENT ON COLUMN public.term_versions.source_citation IS 'Academic citation for this temporal version meaning (e.g., dictionary reference, paper, etc.)';


--
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
-- Name: text_segments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.text_segments_id_seq OWNED BY public.text_segments.id;


--
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
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: document_embeddings id; Type: DEFAULT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.document_embeddings ALTER COLUMN id SET DEFAULT nextval('public.document_embeddings_id_seq'::regclass);


--
-- Name: documents id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.documents ALTER COLUMN id SET DEFAULT nextval('public.documents_id_seq'::regclass);


--
-- Name: domains id; Type: DEFAULT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.domains ALTER COLUMN id SET DEFAULT nextval('public.domains_id_seq'::regclass);


--
-- Name: experiments id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.experiments ALTER COLUMN id SET DEFAULT nextval('public.experiments_id_seq'::regclass);


--
-- Name: extracted_entities id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.extracted_entities ALTER COLUMN id SET DEFAULT nextval('public.extracted_entities_id_seq'::regclass);


--
-- Name: ontologies id; Type: DEFAULT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.ontologies ALTER COLUMN id SET DEFAULT nextval('public.ontologies_id_seq'::regclass);


--
-- Name: ontology_entities id; Type: DEFAULT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.ontology_entities ALTER COLUMN id SET DEFAULT nextval('public.ontology_entities_id_seq'::regclass);


--
-- Name: ontology_mappings id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ontology_mappings ALTER COLUMN id SET DEFAULT nextval('public.ontology_mappings_id_seq'::regclass);


--
-- Name: ontology_versions id; Type: DEFAULT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.ontology_versions ALTER COLUMN id SET DEFAULT nextval('public.ontology_versions_id_seq'::regclass);


--
-- Name: processing_jobs id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.processing_jobs ALTER COLUMN id SET DEFAULT nextval('public.processing_jobs_id_seq'::regclass);


--
-- Name: search_history id; Type: DEFAULT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.search_history ALTER COLUMN id SET DEFAULT nextval('public.search_history_id_seq'::regclass);


--
-- Name: text_segments id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.text_segments ALTER COLUMN id SET DEFAULT nextval('public.text_segments_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: analysis_agents analysis_agents_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.analysis_agents
    ADD CONSTRAINT analysis_agents_pkey PRIMARY KEY (id);


--
-- Name: context_anchors context_anchors_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.context_anchors
    ADD CONSTRAINT context_anchors_pkey PRIMARY KEY (id);


--
-- Name: document_embeddings document_embeddings_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.document_embeddings
    ADD CONSTRAINT document_embeddings_pkey PRIMARY KEY (id);


--
-- Name: documents documents_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (id);


--
-- Name: domains domains_name_key; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.domains
    ADD CONSTRAINT domains_name_key UNIQUE (name);


--
-- Name: domains domains_namespace_uri_key; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.domains
    ADD CONSTRAINT domains_namespace_uri_key UNIQUE (namespace_uri);


--
-- Name: domains domains_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.domains
    ADD CONSTRAINT domains_pkey PRIMARY KEY (id);


--
-- Name: domains domains_uuid_key; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.domains
    ADD CONSTRAINT domains_uuid_key UNIQUE (uuid);


--
-- Name: experiment_documents experiment_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.experiment_documents
    ADD CONSTRAINT experiment_documents_pkey PRIMARY KEY (experiment_id, document_id);


--
-- Name: experiment_references experiment_references_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.experiment_references
    ADD CONSTRAINT experiment_references_pkey PRIMARY KEY (experiment_id, reference_id);


--
-- Name: experiments experiments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.experiments
    ADD CONSTRAINT experiments_pkey PRIMARY KEY (id);


--
-- Name: extracted_entities extracted_entities_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.extracted_entities
    ADD CONSTRAINT extracted_entities_pkey PRIMARY KEY (id);


--
-- Name: fuzziness_adjustments fuzziness_adjustments_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.fuzziness_adjustments
    ADD CONSTRAINT fuzziness_adjustments_pkey PRIMARY KEY (id);


--
-- Name: ontologies ontologies_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.ontologies
    ADD CONSTRAINT ontologies_pkey PRIMARY KEY (id);


--
-- Name: ontologies ontologies_uuid_key; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.ontologies
    ADD CONSTRAINT ontologies_uuid_key UNIQUE (uuid);


--
-- Name: ontology_entities ontology_entities_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.ontology_entities
    ADD CONSTRAINT ontology_entities_pkey PRIMARY KEY (id);


--
-- Name: ontology_mappings ontology_mappings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ontology_mappings
    ADD CONSTRAINT ontology_mappings_pkey PRIMARY KEY (id);


--
-- Name: ontology_versions ontology_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.ontology_versions
    ADD CONSTRAINT ontology_versions_pkey PRIMARY KEY (id);


--
-- Name: processing_jobs processing_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.processing_jobs
    ADD CONSTRAINT processing_jobs_pkey PRIMARY KEY (id);


--
-- Name: provenance_chains provenance_chains_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.provenance_chains
    ADD CONSTRAINT provenance_chains_pkey PRIMARY KEY (id);


--
-- Name: search_history search_history_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.search_history
    ADD CONSTRAINT search_history_pkey PRIMARY KEY (id);


--
-- Name: semantic_drift_activities semantic_drift_activities_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.semantic_drift_activities
    ADD CONSTRAINT semantic_drift_activities_pkey PRIMARY KEY (id);


--
-- Name: term_version_anchors term_version_anchors_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.term_version_anchors
    ADD CONSTRAINT term_version_anchors_pkey PRIMARY KEY (id);


--
-- Name: term_version_anchors term_version_anchors_term_version_id_context_anchor_id_key; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.term_version_anchors
    ADD CONSTRAINT term_version_anchors_term_version_id_context_anchor_id_key UNIQUE (term_version_id, context_anchor_id);


--
-- Name: term_versions term_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.term_versions
    ADD CONSTRAINT term_versions_pkey PRIMARY KEY (id);


--
-- Name: terms terms_pkey; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.terms
    ADD CONSTRAINT terms_pkey PRIMARY KEY (id);


--
-- Name: terms terms_term_text_created_by_key; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.terms
    ADD CONSTRAINT terms_term_text_created_by_key UNIQUE (term_text, created_by);


--
-- Name: text_segments text_segments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.text_segments
    ADD CONSTRAINT text_segments_pkey PRIMARY KEY (id);


--
-- Name: ontology_versions uq_ontology_version; Type: CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.ontology_versions
    ADD CONSTRAINT uq_ontology_version UNIQUE (ontology_id, version_number);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_analysis_agents_active; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_analysis_agents_active ON public.analysis_agents USING btree (is_active) WHERE (is_active = true);


--
-- Name: idx_analysis_agents_type; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_analysis_agents_type ON public.analysis_agents USING btree (agent_type);


--
-- Name: idx_context_anchors_frequency; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_context_anchors_frequency ON public.context_anchors USING btree (frequency DESC);


--
-- Name: idx_context_anchors_term; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_context_anchors_term ON public.context_anchors USING btree (anchor_term);


--
-- Name: idx_documents_parent; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_documents_parent ON public.documents USING btree (parent_document_id);


--
-- Name: idx_documents_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_documents_type ON public.documents USING btree (document_type);


--
-- Name: idx_drift_activities_agent; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_drift_activities_agent ON public.semantic_drift_activities USING btree (was_associated_with);


--
-- Name: idx_drift_activities_generated_entity; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_drift_activities_generated_entity ON public.semantic_drift_activities USING btree (generated_entity);


--
-- Name: idx_drift_activities_periods; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_drift_activities_periods ON public.semantic_drift_activities USING btree (start_period, end_period);


--
-- Name: idx_drift_activities_status; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_drift_activities_status ON public.semantic_drift_activities USING btree (activity_status);


--
-- Name: idx_drift_activities_used_entity; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_drift_activities_used_entity ON public.semantic_drift_activities USING btree (used_entity);


--
-- Name: idx_embeddings_document; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_embeddings_document ON public.document_embeddings USING btree (document_id);


--
-- Name: idx_embeddings_model; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_embeddings_model ON public.document_embeddings USING btree (model_name);


--
-- Name: idx_embeddings_term_period; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_embeddings_term_period ON public.document_embeddings USING btree (term, period);


--
-- Name: idx_embeddings_vector; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_embeddings_vector ON public.document_embeddings USING hnsw (embedding public.vector_cosine_ops);


--
-- Name: idx_entity_label; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_entity_label ON public.ontology_entities USING btree (label);


--
-- Name: idx_entity_type; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_entity_type ON public.ontology_entities USING btree (entity_type);


--
-- Name: idx_experiment_references_experiment; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_experiment_references_experiment ON public.experiment_references USING btree (experiment_id);


--
-- Name: idx_experiment_references_reference; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_experiment_references_reference ON public.experiment_references USING btree (reference_id);


--
-- Name: idx_fuzziness_adjustments_user; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_fuzziness_adjustments_user ON public.fuzziness_adjustments USING btree (adjusted_by);


--
-- Name: idx_fuzziness_adjustments_version; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_fuzziness_adjustments_version ON public.fuzziness_adjustments USING btree (term_version_id);


--
-- Name: idx_ontology_entity; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_ontology_entity ON public.ontology_entities USING btree (ontology_id, entity_type);


--
-- Name: idx_term_version_anchors_anchor; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_term_version_anchors_anchor ON public.term_version_anchors USING btree (context_anchor_id);


--
-- Name: idx_term_version_anchors_similarity; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_term_version_anchors_similarity ON public.term_version_anchors USING btree (similarity_score DESC);


--
-- Name: idx_term_version_anchors_version; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_term_version_anchors_version ON public.term_version_anchors USING btree (term_version_id);


--
-- Name: idx_term_versions_corpus; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_term_versions_corpus ON public.term_versions USING btree (corpus_source);


--
-- Name: idx_term_versions_current; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_term_versions_current ON public.term_versions USING btree (is_current) WHERE (is_current = true);


--
-- Name: idx_term_versions_fuzziness; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_term_versions_fuzziness ON public.term_versions USING btree (fuzziness_score);


--
-- Name: idx_term_versions_temporal_period; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_term_versions_temporal_period ON public.term_versions USING btree (temporal_period);


--
-- Name: idx_term_versions_temporal_years; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_term_versions_temporal_years ON public.term_versions USING btree (temporal_start_year, temporal_end_year);


--
-- Name: idx_term_versions_term_id; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_term_versions_term_id ON public.term_versions USING btree (term_id);


--
-- Name: idx_terms_created_by; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_terms_created_by ON public.terms USING btree (created_by);


--
-- Name: idx_terms_research_domain; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_terms_research_domain ON public.terms USING btree (research_domain);


--
-- Name: idx_terms_status; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_terms_status ON public.terms USING btree (status);


--
-- Name: idx_terms_text; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX idx_terms_text ON public.terms USING btree (term_text);


--
-- Name: ix_analysis_agents_agent_type; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_analysis_agents_agent_type ON public.analysis_agents USING btree (agent_type);


--
-- Name: ix_analysis_agents_is_active; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_analysis_agents_is_active ON public.analysis_agents USING btree (is_active);


--
-- Name: ix_context_anchors_anchor_term; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE UNIQUE INDEX ix_context_anchors_anchor_term ON public.context_anchors USING btree (anchor_term);


--
-- Name: ix_context_anchors_frequency; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_context_anchors_frequency ON public.context_anchors USING btree (frequency);


--
-- Name: ix_documents_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_documents_user_id ON public.documents USING btree (user_id);


--
-- Name: ix_entity_embedding_vector; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_entity_embedding_vector ON public.ontology_entities USING ivfflat (embedding public.vector_cosine_ops) WITH (lists='100');


--
-- Name: ix_experiments_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_experiments_user_id ON public.experiments USING btree (user_id);


--
-- Name: ix_extracted_entities_processing_job_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_extracted_entities_processing_job_id ON public.extracted_entities USING btree (processing_job_id);


--
-- Name: ix_extracted_entities_text_segment_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_extracted_entities_text_segment_id ON public.extracted_entities USING btree (text_segment_id);


--
-- Name: ix_fuzziness_adjustments_adjusted_by; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_fuzziness_adjustments_adjusted_by ON public.fuzziness_adjustments USING btree (adjusted_by);


--
-- Name: ix_fuzziness_adjustments_term_version_id; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_fuzziness_adjustments_term_version_id ON public.fuzziness_adjustments USING btree (term_version_id);


--
-- Name: ix_ontology_mappings_extracted_entity_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ontology_mappings_extracted_entity_id ON public.ontology_mappings USING btree (extracted_entity_id);


--
-- Name: ix_processing_jobs_document_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_processing_jobs_document_id ON public.processing_jobs USING btree (document_id);


--
-- Name: ix_processing_jobs_parent_job_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_processing_jobs_parent_job_id ON public.processing_jobs USING btree (parent_job_id);


--
-- Name: ix_processing_jobs_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_processing_jobs_user_id ON public.processing_jobs USING btree (user_id);


--
-- Name: ix_semantic_drift_activities_activity_status; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_semantic_drift_activities_activity_status ON public.semantic_drift_activities USING btree (activity_status);


--
-- Name: ix_semantic_drift_activities_end_period; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_semantic_drift_activities_end_period ON public.semantic_drift_activities USING btree (end_period);


--
-- Name: ix_semantic_drift_activities_generated_entity; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_semantic_drift_activities_generated_entity ON public.semantic_drift_activities USING btree (generated_entity);


--
-- Name: ix_semantic_drift_activities_start_period; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_semantic_drift_activities_start_period ON public.semantic_drift_activities USING btree (start_period);


--
-- Name: ix_semantic_drift_activities_used_entity; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_semantic_drift_activities_used_entity ON public.semantic_drift_activities USING btree (used_entity);


--
-- Name: ix_semantic_drift_activities_was_associated_with; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_semantic_drift_activities_was_associated_with ON public.semantic_drift_activities USING btree (was_associated_with);


--
-- Name: ix_term_versions_corpus_source; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_term_versions_corpus_source ON public.term_versions USING btree (corpus_source);


--
-- Name: ix_term_versions_is_current; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_term_versions_is_current ON public.term_versions USING btree (is_current);


--
-- Name: ix_term_versions_temporal_end_year; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_term_versions_temporal_end_year ON public.term_versions USING btree (temporal_end_year);


--
-- Name: ix_term_versions_temporal_period; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_term_versions_temporal_period ON public.term_versions USING btree (temporal_period);


--
-- Name: ix_term_versions_temporal_start_year; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_term_versions_temporal_start_year ON public.term_versions USING btree (temporal_start_year);


--
-- Name: ix_term_versions_term_id; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_term_versions_term_id ON public.term_versions USING btree (term_id);


--
-- Name: ix_terms_created_by; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_terms_created_by ON public.terms USING btree (created_by);


--
-- Name: ix_terms_research_domain; Type: INDEX; Schema: public; Owner: ontextract_user
--

CREATE INDEX ix_terms_research_domain ON public.terms USING btree (research_domain);


--
-- Name: ix_text_segments_document_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_text_segments_document_id ON public.text_segments USING btree (document_id);


--
-- Name: ix_text_segments_parent_segment_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_text_segments_parent_segment_id ON public.text_segments USING btree (parent_segment_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_username ON public.users USING btree (username);


--
-- Name: term_version_anchors trigger_update_context_anchor_frequency; Type: TRIGGER; Schema: public; Owner: ontextract_user
--

CREATE TRIGGER trigger_update_context_anchor_frequency AFTER INSERT OR DELETE ON public.term_version_anchors FOR EACH ROW EXECUTE FUNCTION public.update_context_anchor_frequency();


--
-- Name: terms trigger_update_terms_updated_at; Type: TRIGGER; Schema: public; Owner: ontextract_user
--

CREATE TRIGGER trigger_update_terms_updated_at BEFORE UPDATE ON public.terms FOR EACH ROW EXECUTE FUNCTION public.update_terms_updated_at();


--
-- Name: analysis_agents analysis_agents_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.analysis_agents
    ADD CONSTRAINT analysis_agents_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: context_anchors context_anchors_first_used_in_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.context_anchors
    ADD CONSTRAINT context_anchors_first_used_in_fkey FOREIGN KEY (first_used_in) REFERENCES public.term_versions(id);


--
-- Name: context_anchors context_anchors_last_used_in_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.context_anchors
    ADD CONSTRAINT context_anchors_last_used_in_fkey FOREIGN KEY (last_used_in) REFERENCES public.term_versions(id);


--
-- Name: document_embeddings document_embeddings_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.document_embeddings
    ADD CONSTRAINT document_embeddings_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id);


--
-- Name: documents documents_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: experiment_documents experiment_documents_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.experiment_documents
    ADD CONSTRAINT experiment_documents_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id);


--
-- Name: experiment_documents experiment_documents_experiment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.experiment_documents
    ADD CONSTRAINT experiment_documents_experiment_id_fkey FOREIGN KEY (experiment_id) REFERENCES public.experiments(id);


--
-- Name: experiment_references experiment_references_experiment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.experiment_references
    ADD CONSTRAINT experiment_references_experiment_id_fkey FOREIGN KEY (experiment_id) REFERENCES public.experiments(id);


--
-- Name: experiment_references experiment_references_reference_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.experiment_references
    ADD CONSTRAINT experiment_references_reference_id_fkey FOREIGN KEY (reference_id) REFERENCES public.documents(id);


--
-- Name: experiments experiments_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.experiments
    ADD CONSTRAINT experiments_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: extracted_entities extracted_entities_processing_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.extracted_entities
    ADD CONSTRAINT extracted_entities_processing_job_id_fkey FOREIGN KEY (processing_job_id) REFERENCES public.processing_jobs(id);


--
-- Name: extracted_entities extracted_entities_text_segment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.extracted_entities
    ADD CONSTRAINT extracted_entities_text_segment_id_fkey FOREIGN KEY (text_segment_id) REFERENCES public.text_segments(id);


--
-- Name: documents fk_documents_parent_document_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT fk_documents_parent_document_id FOREIGN KEY (parent_document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: fuzziness_adjustments fuzziness_adjustments_adjusted_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.fuzziness_adjustments
    ADD CONSTRAINT fuzziness_adjustments_adjusted_by_fkey FOREIGN KEY (adjusted_by) REFERENCES public.users(id);


--
-- Name: fuzziness_adjustments fuzziness_adjustments_term_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.fuzziness_adjustments
    ADD CONSTRAINT fuzziness_adjustments_term_version_id_fkey FOREIGN KEY (term_version_id) REFERENCES public.term_versions(id);


--
-- Name: ontologies ontologies_domain_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.ontologies
    ADD CONSTRAINT ontologies_domain_id_fkey FOREIGN KEY (domain_id) REFERENCES public.domains(id);


--
-- Name: ontologies ontologies_parent_ontology_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.ontologies
    ADD CONSTRAINT ontologies_parent_ontology_id_fkey FOREIGN KEY (parent_ontology_id) REFERENCES public.ontologies(id);


--
-- Name: ontology_entities ontology_entities_ontology_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.ontology_entities
    ADD CONSTRAINT ontology_entities_ontology_id_fkey FOREIGN KEY (ontology_id) REFERENCES public.ontologies(id);


--
-- Name: ontology_mappings ontology_mappings_extracted_entity_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ontology_mappings
    ADD CONSTRAINT ontology_mappings_extracted_entity_id_fkey FOREIGN KEY (extracted_entity_id) REFERENCES public.extracted_entities(id);


--
-- Name: ontology_versions ontology_versions_ontology_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.ontology_versions
    ADD CONSTRAINT ontology_versions_ontology_id_fkey FOREIGN KEY (ontology_id) REFERENCES public.ontologies(id);


--
-- Name: processing_jobs processing_jobs_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.processing_jobs
    ADD CONSTRAINT processing_jobs_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id);


--
-- Name: processing_jobs processing_jobs_parent_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.processing_jobs
    ADD CONSTRAINT processing_jobs_parent_job_id_fkey FOREIGN KEY (parent_job_id) REFERENCES public.processing_jobs(id);


--
-- Name: processing_jobs processing_jobs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.processing_jobs
    ADD CONSTRAINT processing_jobs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: provenance_chains provenance_chains_derivation_activity_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.provenance_chains
    ADD CONSTRAINT provenance_chains_derivation_activity_fkey FOREIGN KEY (derivation_activity) REFERENCES public.semantic_drift_activities(id);


--
-- Name: semantic_drift_activities semantic_drift_activities_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.semantic_drift_activities
    ADD CONSTRAINT semantic_drift_activities_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: semantic_drift_activities semantic_drift_activities_generated_entity_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.semantic_drift_activities
    ADD CONSTRAINT semantic_drift_activities_generated_entity_fkey FOREIGN KEY (generated_entity) REFERENCES public.term_versions(id);


--
-- Name: semantic_drift_activities semantic_drift_activities_used_entity_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.semantic_drift_activities
    ADD CONSTRAINT semantic_drift_activities_used_entity_fkey FOREIGN KEY (used_entity) REFERENCES public.term_versions(id);


--
-- Name: semantic_drift_activities semantic_drift_activities_was_associated_with_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.semantic_drift_activities
    ADD CONSTRAINT semantic_drift_activities_was_associated_with_fkey FOREIGN KEY (was_associated_with) REFERENCES public.analysis_agents(id);


--
-- Name: term_version_anchors term_version_anchors_context_anchor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.term_version_anchors
    ADD CONSTRAINT term_version_anchors_context_anchor_id_fkey FOREIGN KEY (context_anchor_id) REFERENCES public.context_anchors(id);


--
-- Name: term_version_anchors term_version_anchors_term_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.term_version_anchors
    ADD CONSTRAINT term_version_anchors_term_version_id_fkey FOREIGN KEY (term_version_id) REFERENCES public.term_versions(id);


--
-- Name: term_versions term_versions_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.term_versions
    ADD CONSTRAINT term_versions_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: term_versions term_versions_term_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.term_versions
    ADD CONSTRAINT term_versions_term_id_fkey FOREIGN KEY (term_id) REFERENCES public.terms(id);


--
-- Name: term_versions term_versions_was_derived_from_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.term_versions
    ADD CONSTRAINT term_versions_was_derived_from_fkey FOREIGN KEY (was_derived_from) REFERENCES public.term_versions(id);


--
-- Name: terms terms_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.terms
    ADD CONSTRAINT terms_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: terms terms_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ontextract_user
--

ALTER TABLE ONLY public.terms
    ADD CONSTRAINT terms_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public.users(id);


--
-- Name: text_segments text_segments_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.text_segments
    ADD CONSTRAINT text_segments_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id);


--
-- Name: text_segments text_segments_parent_segment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.text_segments
    ADD CONSTRAINT text_segments_parent_segment_id_fkey FOREIGN KEY (parent_segment_id) REFERENCES public.text_segments(id);


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT ALL ON SCHEMA public TO ontextract_user;


--
-- Name: TABLE documents; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.documents TO ontextract_user;


--
-- Name: SEQUENCE documents_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.documents_id_seq TO ontextract_user;


--
-- Name: TABLE experiment_documents; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.experiment_documents TO ontextract_user;


--
-- Name: TABLE experiment_references; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.experiment_references TO ontextract_user;


--
-- Name: TABLE experiments; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.experiments TO ontextract_user;


--
-- Name: SEQUENCE experiments_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.experiments_id_seq TO ontextract_user;


--
-- Name: TABLE extracted_entities; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.extracted_entities TO ontextract_user;


--
-- Name: SEQUENCE extracted_entities_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.extracted_entities_id_seq TO ontextract_user;


--
-- Name: TABLE ontology_mappings; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.ontology_mappings TO ontextract_user;


--
-- Name: SEQUENCE ontology_mappings_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.ontology_mappings_id_seq TO ontextract_user;


--
-- Name: TABLE processing_jobs; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.processing_jobs TO ontextract_user;


--
-- Name: SEQUENCE processing_jobs_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.processing_jobs_id_seq TO ontextract_user;


--
-- Name: TABLE text_segments; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.text_segments TO ontextract_user;


--
-- Name: SEQUENCE text_segments_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.text_segments_id_seq TO ontextract_user;


--
-- Name: TABLE users; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.users TO ontextract_user;


--
-- Name: SEQUENCE users_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.users_id_seq TO ontextract_user;


--
-- PostgreSQL database dump complete
--

\unrestrict wuwkqIWPiWStDe9iqczqagv4EF0JEFc2bcobT6yo7XohxM0QhBWc7DeEKivL0Bo

