--
-- PostgreSQL database dump
--

\restrict yrZzcVew8KrnIM6lSLpaDnpW7WkrIsCAUPFWvMShZoZ469YhB44fcnvxKrTKPng

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
-- Data for Name: analysis_agents; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.analysis_agents (id, agent_type, name, description, version, algorithm_type, model_parameters, training_data, expertise_domain, institutional_affiliation, created_at, is_active, user_id) FROM stdin;
4a32b8b0-8581-4975-8785-929ec8c4878f	Person	Manual Curation	Human curator performing manual semantic analysis	1.0	Manual_Curation	\N	\N	\N	\N	\N	\N	\N
f959c050-3cc8-4549-a2f2-d3894198ca53	SoftwareAgent	HistBERT Temporal Embedding Alignment	Historical BERT model for temporal semantic alignment	1.0	HistBERT	\N	\N	\N	\N	\N	\N	\N
fdacd5b5-4b12-41fe-83d2-172a5581e53e	SoftwareAgent	Word2Vec Diachronic Analysis	Word2Vec model trained on temporal corpora	1.0	Word2Vec	\N	\N	\N	\N	\N	\N	\N
\.


--
-- Data for Name: context_anchors; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.context_anchors (id, anchor_term, frequency, first_used_in, last_used_in, created_at) FROM stdin;
a50cc9e3-f468-4a60-9278-14fc783189e5	agent	1	\N	\N	2025-08-24 13:18:57.911853-04
466fe463-f97c-40c8-b13f-63c539b619d8	cell	1	\N	\N	2025-08-24 13:26:19.747627-04
0f6ed02a-0d5d-4325-91cf-7f8701b4f480	ontology	1	\N	\N	2025-08-24 13:27:14.07582-04
e52c0e9a-c7b1-43c1-9db8-1e2be5f7af1a	hooligan	2	\N	703b355f-e602-40ad-a470-33a89d008dd8	2025-08-24 14:03:22.104634-04
99267944-387f-4c8d-a0ba-62bbc69d2f4d	usually	2	\N	703b355f-e602-40ad-a470-33a89d008dd8	2025-08-24 14:03:22.110767-04
0bd2bb6f-36f3-46cf-9b60-d7ab53b77fa5	young	2	\N	703b355f-e602-40ad-a470-33a89d008dd8	2025-08-24 14:03:22.113901-04
03406a50-523c-43c3-aeb4-e151c60f442a	engages	2	\N	703b355f-e602-40ad-a470-33a89d008dd8	2025-08-24 14:03:22.118188-04
187a15c2-0041-4dc1-a4fe-c6d5efc265e9	granularity	1	\N	\N	2025-08-24 13:37:42.66053-04
4e4d398a-e465-4d5a-a743-903ef78bf7d5	consisting	1	\N	\N	2025-08-24 13:37:42.669698-04
bbe2884b-d4b2-44ef-a40f-5bf2bc95d6af	appearing	1	\N	\N	2025-08-24 13:37:42.67267-04
c794432d-7542-45c4-9eb3-56f383f0a232	consist	1	\N	\N	2025-08-24 13:37:42.675239-04
20bbf849-cb9f-4bd1-b242-68da857075e3	finely	1	\N	\N	2025-08-24 13:37:42.677822-04
be420c20-5278-4184-a725-3df467434af4	detailed	1	\N	\N	2025-08-24 13:37:42.680428-04
\.


--
-- Data for Name: documents; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.documents (id, title, content_type, document_type, reference_subtype, file_type, original_filename, file_path, file_size, source_metadata, content, content_preview, detected_language, language_confidence, status, word_count, character_count, created_at, updated_at, processed_at, user_id, embedding, parent_document_id) FROM stdin;
53	OED: role_nn01	text	reference	dictionary_oed	\N	\N	\N	\N	{"source": "OED Researcher API", "oed_entry_id": "role_nn01", "headword": "role_nn01", "part_of_speech": null, "oed_api_word_url": "https://oed-researcher-api.oxfordlanguages.com/oed/api/v0.2/word/role_nn01/", "oed_web_search_url": "https://www.oed.com/search/dictionary/?q=role_nn01", "selected_senses": [{"sense_id": "role_nn01", "label": "", "definition": "A person's allotted share, part, or duty in life and society; the character, place, or status assigned to or assumed"}]}	OED entry: role_nn01\nHeadword: role_nn01\nSelected senses: role_nn01	OED entry: role_nn01\nHeadword: role_nn01\nSelected senses: role_nn01	\N	\N	completed	8	67	2025-08-27 12:52:00.419653	2025-08-27 12:52:00.419657	\N	1	\N	\N
54	OED: role_vb01	text	reference	dictionary_oed	\N	\N	\N	\N	{"source": "OED Researcher API", "oed_entry_id": "role_vb01", "headword": "role_vb01", "part_of_speech": null, "oed_api_word_url": "https://oed-researcher-api.oxfordlanguages.com/oed/api/v0.2/word/role_vb01/", "oed_web_search_url": "https://www.oed.com/search/dictionary/?q=role_vb01", "selected_senses": [{"sense_id": "role_vb01", "label": "", "definition": "transitive. To provide with a role indicator."}]}	OED entry: role_vb01\nHeadword: role_vb01\nSelected senses: role_vb01	OED entry: role_vb01\nHeadword: role_vb01\nSelected senses: role_vb01	\N	\N	completed	8	67	2025-08-27 12:52:00.419657	2025-08-27 12:52:00.419658	\N	1	\N	\N
59	Schwartz - 2016 - Ethical Decision-Making Theory An Integrated Appr	file	document	\N	pdf	Schwartz - 2016 - Ethical Decision-Making Theory An Integrated Appr.pdf	uploads/1e38d89e9c874540b54b630eaaa274da_Schwartz_-_2016_-_Ethical_Decision-Making_Theory_An_Integrated_Appr.pdf	544528	\N	Ethical Decision-Making Theory: An Integrated Approach\nMark S. Schwartz 1\nReceived: 15 December 2014 / Accepted: 23 September 2015 / Published online: 26 October 2015\n/C211 Springer Science+Business Media Dordrecht 2015\nAbstract Ethical decision-making (EDM) descriptive\ntheoretical models often conﬂict with each other and typ-\nically lack comprehensiveness. To address this deﬁciency,\na revised EDM model is proposed that consolidates and\nattempts to bridge together the varying and sometimes\ndirectly conﬂicting propositions and perspectives that have\nbeen advanced. To do so, the paper is organized as follows.\nFirst, a review of the various theoretical models of EDM is\nprovided. These models can generally be divided into\n(a) rationalist-based (i.e., reason); and (b) non-rationalist-\nbased (i.e., intuition and emotion). Second, the proposed\nmodel, called ‘Integrated Ethical Decision Making,’ is\nintroduced in order to ﬁll the gaps and bridge the current\ndivide in EDM theory. The individual and situational fac-\ntors as well as the process of the proposed model are then\ndescribed. Third, the academic and managerial implica-\ntions of the proposed model are discussed. Finally, the\nlimitations of the proposed model are presented.\nKeywords Emotion /C1Ethical decision making /C1\nIntuition /C1Moral rationalization /C1Moral reasoning\nIntroduction\nWhile much has been discovered regarding the ethical\ndecision-making (EDM) process within business organi-\nzations, a great deal remains unknown. The importance of\nEDM is no longer in doubt, given the extent of illegal and\nunethical activity that continues to take place every year\nand the resultant costs to societal stakeholders including\nshareholders, employees, consumers, and the natural\nenvironment (U.S. Sentencing Commission 2014; Asso-\nciation of Certiﬁed Fraud Examiners 2014). Unethical\nactivity by individuals continues despite the best efforts of\nbusiness organizations to implement comprehensive ethics\nprograms, including codes of ethics, ethics training, and\nwhistleblowing hotlines (Ethics Resource Center 2014;\nWebley 2011) and despite the extent to which business\nschools around the world teach the subject of business\nethics (Rossouw and Stu ¨ ckelberger 2012). The signiﬁcant\nnegative yet potentially preventable costs to society\nresulting from the unethical actions of individual ﬁrm\nagents suggest that ethical decision making might be\nconsidered one of the most important processes to better\nunderstand, not only for the academic management ﬁeld,\nbut also for the corporate community and society at large\n(Trevin˜o 1986).\nThere have however been important developments\nthrough academic research over recent years leading to an\nimproved understanding of EDM (see Trevin ˜o et al. 2006;\nTenbrunsel and Smith-Crowe 2008) including how to\nmeasure each of its constructs and dimensions (Agle et al.\n2014). Building on and borrowing from a series of aca-\ndemic disciplines and theories including moral philoso-\nphy, moral psychology, social psychology, social\neconomics, organizational behavior, criminology, behav-\nioral science, behavioral ethics, cognitive neuroscience,\nand business ethics, a number of descriptive EDM theo-\nretical models have been proposed to help explain the\ndecision-making process of individuals leading to ethical\nor unethical behavior or actions (see Torres 2001).\nCommonly referred to as EDM theory, these descriptive\n& Mark S. Schwartz\nschwartz@yorku.ca\n1 School of Administrative Studies, Faculty of Liberal Arts and\nProfessional Studies, York University, 4700 Keele Street,\nToronto, ON M3J 1P3, Canada\n123\nJ Bus Ethics (2016) 139:755–776\nDOI 10.1007/s10551-015-2886-8\n\ntheoretical EDM frameworks (as opposed to normative\nEDM frameworks) help to explain how cognitive pro-\ncesses (i.e., reason or intuition) or affective processes\n(i.e., emotion) operate within the brain (Reynolds 2006a;\nSalvador and Folger 2009; Greene et al. 2001) leading to\nmoral judgment and behavior on the part of individuals.\nTo further enhance our understanding, these theoretical\nmodels typically present the EDM process as a series of\ntemporal and sequential process stages, typically begin-\nning with initial awareness or recognition of an ethical\nissue leading to a moral judgment, intention to act, and\nﬁnally to behavior (Rest 1984, 1986).\n1\nIn addition to explaining the EDM process, most theo-\nretical EDM models also include a set of individual, orga-\nnizational, or situational-related variables and indicate at\nwhich stage of EDM (i.e., awareness, judgment, intention,\nor behavior) they can exert a causal effect or a moderating\ninﬂuence. Based on these theoretical EDM models, hun-\ndreds of empirical studies, both qualitative and quantitative\nin nature, along with several meta-studies, have now been\nconducted to try to verify and explain exactly which inde-\npendent factors or variables actually inﬂuence the decision\nmaking of individuals, including whether one stage of EDM\nnecessarily leads to the next stage (see Ford and Richardson\n1994; Loe et al. 2000; O’Fallon and Butterﬁeld 2005; Craft\n2013; Lehnert et al. 2015).\nWhile such theoretical and empirical research has\nproven helpful to better understand what has been referred\nto as the ‘black box’ of EDM (Liedka 1989, p. 805;\nTenbrunsel and Smith-Crowe 2008, p. 584), the relevance\nor explanatory power of the theoretical and empirical\nresearch can at least initially be questioned given the lack\nof consistent ﬁndings (O’Fallon and Butterﬁeld 2005;\nCraft 2013; Pan and Sparks 2012). This may be partially\nattributable due to the research methods being used (e.g.,\nthe use of scenarios/vignettes, surveys, student samples,\nor self-reporting, see Randall and Gibson 1990; O’Fallon\nand Butterﬁeld 2005) or the diversity or quality of the\nresearch measurement instruments being utilized (see\nMudrack and Mason 2013; Casali 2011). Another possi-\nbility may be that EDM is simply too complex a neuro-\ncognitive-affective process involving too many inter-re-\nlated or undiscoverable variables being processed by our\nbrains preventing any possible generalizable conclusions.\nIt may also be that the predictive ability of any theoretical\nEDM model will be limited to activity that more clearly\nconstitutes ethical or unethical behavior, rather than pre-\ndicting behavior involving more complex ethical dilem-\nmas where achieving normative consensus over what even\nconstitutes ‘ethical’ behavior can often prove to be\nelusive.\n2 The challenges and complexity of EDM have\neven led some researchers to suggest a ‘punch bowl’ or\n‘garbage can’ approach to EDM, which assumes that\nresearchers will never know exactly what takes place\nleading to ethical judgments in that only what goes into or\nout of the process is capable of being analyzed (e.g.,\nSchminke 1998, p. 207).\nOne other possible explanation for the lack of consistent\nempirical ﬁndings however is that further reﬁnements to\nEDM descriptive theory models if undertaken might\nimprove the models’ explanatory and predictive capability\nleading to more relevant and consistent empirical ﬁndings.\nIt is this latter possibility that this paper seeks to address.\nFor example, a review of the descriptive EDM theoretical\nmodels proposed to date (Tenbrunsel and Smith-Crowe\n2008) along with consideration of the more recent chal-\nlenges and criticisms raised with respect to EDM research\n(Haidt 2001; Sonenshein 2007; Whittier et al. 2006;B a r -\ntlett 2003) suggests that there is signiﬁcant room for\nimprovement in theoretical EDM models. Following their\nreview of the empirical EDM research, O’Fallon and\nButterﬁeld state ( 2005, p. 399): ‘‘If the ﬁeld of descriptive\nethics is to move forward to strengthen our understanding\nof the EDM process, it is imperative that future studies\nfocus more attention on theory development.’’ According\nto Tenbrunsel and Smith-Crowe ( 2008, p. 547): ‘‘ …many\n[studies] are still atheoretical or uni-theoretical, relying on\na single theory.’’ They then reﬂect on the deﬁciency in\nEDM theory: ‘‘Unlike in the past, researchers no longer\nneed to justify their rationale for studying ethics; instead,\ntheir attention needs to focus on developing a more com-\nprehensive theoretical platform upon which empirical work\nin behavioral ethics can continue’’ (Tenbrunsel and Smith-\nCrowe 2008, p. 593). In other words, the current dis-\nagreement among scholars over which theoretical EDM\nmodel (if any) is the most appropriate, especially when\nengaging in empirical research, needs to be addressed.\nThis paper will attempt to contribute to EDM literature\nby focusing on the primary gaps in the theoretical EDM\nmodels that have been identiﬁed. By doing so, the research\nobjective is to develop a theoretical EDM model that not\nonly captures and builds upon the current state of EDM, but\nalso consolidates and attempts to bridge together the vary-\ning and sometimes directly conﬂicting propositions and\nperspectives that have been advanced. In other words, the\npaper will attempt to incorporate and depict what has not\nalways been clearly portrayed in any proposed EDM model\nin a more integrated manner. The most important or key\nintegration being advanced is the combined and inter-\n1 For ease of reference, ‘ethics’ or ‘ethical’ are considered throughout\nthe paper to be synonymous with ‘morality’ or ‘moral.’\n2 For example, Ferrell and Gresham state ( 1985, p. 87): ‘ ‘Absence of\na clear consensus about ethical conduct …has resulted in much\nconfusion among academicians …’’\n756 M. S. Schwartz\n123\n\nrelated impact of intuition–emotion along with reason–ra-\ntionalization on the moral judgment stage of EDM. In\naddition, to address the proliferation of individual, organi-\nzational, and situational/issue-related factors being applied\nin EDM research, several core constructs are proposed in\norder to better capture their corresponding sub-variables,\nsuch as an individual’s ‘moral capacity’ and an organiza-\ntion’s ‘ethical infrastructure.’ Other important features of\nthe revised model include (i) the presence of ‘lack of moral\nawareness’ leading to behavior; (ii) the expansion of the\nissue-based EDM variable; (iii) the inclusion of moral\nrationalization; and (iv) the addition of an explicit ‘moral\nconsultation’ stage into the EDM process.\nThe proposed integrated model essentially reﬂects a\nsynthesis of the ‘intuitionist/sentimentalist’ (Haidt 2001),\n‘rationalist’ (Kohlberg 1973; Rest 1986), ‘person-situation\ninteractionist’ (Trevin˜o 1986), and ‘issue-contingent’ (Jones\n1991) approaches to EDM. The revised model attempts to\ndepict the current theoretical ﬁeld of EDM in a relatively\ncomprehensive yet hopefully more coherent and simpliﬁed\nmanner. The intended contribution of the proposed model is\nnot necessarily to offer any particularly new major insights\ninto EDM, but to depict a theoretical platform and schematic\nrepresentation upon which a broader range of EDM\nresearchers, including both rationalists and non-rationalists,\ncan hopefully feel comfortable utilizing in a more cohesive\nand consistent manner. In addition, while ‘is’ does not\nnecessarily imply ‘ought,’ the development of a more robust\ndescriptive EDM model may lead to more effective and\nrelevant normative EDM models which might then have an\neffect on future management or educational practices.\nIn order to propose and depict a reformulated theoretical\nEDM model, the paper will be organized as follows. First, a\nreview of the various theoretical models of EDM will be\nprovided. These models can generally be divided into\n(a) rationalist-based (i.e., reason); and (b) non-rationalist-\nbased (i.e., intuition and emotion). Second, the proposed\nmodel, called ‘Integrated EDM’ (I-EDM), is introduced in\norder to ﬁll the gaps and bridge the current divide in EDM\ntheory. The individual and situational factors as well as the\nprocess of the proposed model are then described. Third,\nthe academic and managerial implications of the proposed\nmodel will be discussed. Finally, the limitations of the\nproposed model are presented.\nSeveral notes of caution are required however. This\nstudy is not intended to provide a comprehensive literature\nreview of the EDM ﬁeld. Only what might be considered to\nbe the most salient or utilized EDM models or research is\nincluded in the discussion.\n3 In addition, each of the EDM\nconstructs or processes is not discussed to the same extent,\nrather those that require modiﬁcation from previous EDM\nmodels are given greater emphasis throughout the paper. In\naddition, the unit of analysis is individuals acting within or\non behalf of business organizations, rather than organiza-\ntional-level ethical decision making.\nFinally, for the purposes of the paper, a few key deﬁ-\nnitions are required. An ethical dilemma is deﬁned as a\nsituation in which an individual must reﬂect upon com-\npeting moral standards and/or stakeholder claims in\ndetermining what is the morally appropriate decision or\naction.\n4 Moral judgment is deﬁned as the determination of\nthe ethically appropriate course of action among potential\nalternatives. Ethical behavior is deﬁned not merely as\nconforming to the legal or moral norms of the larger\ncommunity\n5 (Jones 1991), but consists of behavior sup-\nported by one or more additional moral standards. 6\nReview of the Theoretical Descriptive EDM\nApproaches\nA review of EDM research reveals that there are two\ngeneral categories of EDM theoretical models, those that\nare (a) rationalist-based; and (b) non-rationalist-based. 7\nThe rationalist-based models speciﬁcally assume that the\n3 This is similar to the approach used by Trevin ˜o et al. ( 2006) in their\nliterature review of EDM.\n4 One might try to distinguish situations involving ‘ethical dilemmas’\nfrom those whereby an individual is facing a ‘moral temptation.’\n‘Ethical dilemmas’ can be seen as those more challenging situations\ninvolving ‘right versus right’ or ‘wrong versus wrong’ alternatives,\nsuch as deciding which employee to lay off. ‘Moral temptations’\nhowever involve ‘right versus wrong’ alternatives more directly\nlinked to one’s self-interest, such as deciding whether to steal supplies\nfrom the ofﬁce supply cabinet (see Kidder 1995). For the purposes of\nthe I-EDM model, both ethical dilemmas and moral temptations can\nbe faced by individual decision makers as ethical issues.\n5 Jones states ( 1991, p. 367): ‘‘ …an ethical decision is deﬁned as a\ndecision that is both legal and morally acceptable to the larger\ncommunity. Conversely, an unethical decision is either illegal or\nmorally unacceptable to the larger community.’’ This is too limited a\ndeﬁnition of ‘ethical’ to be utilized for the purposes of properly\nstudying the EDM process. Jones ( 1991, p. 367) himself admits that\nhis deﬁnition of an ethical decision is ‘‘imprecise and relativistic’’ and\nrefers to the difﬁculties of establishing substantive deﬁnitions for\nethical behavior. Others have also suggested that this deﬁnition of\nwhat is ethical is ‘ ‘too relativistic’’ and avoids a precise normative\nposition on right versus wrong (Reynolds 2008; Tenbrunsel and\nSmith-Crowe 2008). In addition, community norms can violate\n‘hypernorms’ (see Donaldson and Dunfee 1999).\n6 While there is an extensive literature on moral theory, the moral\nstandards can be grouped under three general categories: (i) conven-\ntionalist (e.g., industry or corporate codes of ethics); (ii) consequen-\ntialist (e.g., utilitarianism); or (iii) deontological, including\ntrustworthiness, respect, moral rights, and justice/fairness (see\nSchwartz and Carroll 2003; Schwartz 2005).\n7 Another possible way of dividing up EDM models is to categorize\nthose that focus primarily on the disposition of the decision maker,\nversus those that are more interactional (person-situation) in nature.\nSee Tsang ( 2002, p. 25).\nEthical Decision-Making Theory: An Integrated Approach 757\n123\n\nmoral reasoning process dominates the core of the model,\nleading to moral judgment. The non-rationalist-based\nmodels assume that both intuition and emotion dominate the\nmoral judgment process, with moral reasoning playing a\nsecondary ‘after the fact’ explanatory (i.e., reason) or jus-\ntiﬁcatory (i.e., rationalization) role for one’s moral judg-\nment (Haidt 2001; Sonenshein 2007). More recent models\nhowever suggest that rather than reason–rationalization and\nintuition–emotion being mutually exclusive, there is either\na ‘dual-process’ involving two stages or a ‘two-systems’\nprocess whereby there is concurrent interaction between\nintuition (impulsive) and reason (reﬂective) leading to\nmoral judgment (see Reynolds 2006a; Strack and Deutsch\n2004) or between emotion and reason leading to moral\njudgment (Greene et al. 2001). These interactions form the\nbasis of the revised model discussed below. Each group of\nEDM theoretical models will now be brieﬂy outlined.\nRationalist approaches\nThe ﬁrst group of theoretical models explicitly or implicitly\nassumes that a predominantly reason-based process takes\nplace leading to moral judgment. The rationalist approach\nsuggests that upon experiencing an ethical dilemma, the\ndecision maker attempts to resolve conﬂicts through a\nlogical, rational and deliberative cognitive process by\nconsidering and weighing various moral standards that\nmight be in conﬂict with one another. The vast majority of\nempirical EDM researchers appear to rely on this particular\ntheoretical framework when conducting their research.\nFor example, Ferrell and Gresham ( 1985) developed a\n‘multistage contingency’ model of EDM, in which an eth-\nical dilemma arises from the social or cultural environment.\nThe behavior of the decision maker is then affected by two\nsets of ‘contingency factors’ including (1) individual factors\n(i.e., knowledge, values, attitudes, and intentions); and (2)\norganizational factors (i.e., signiﬁcant others including top\nmanagement and peers, and opportunity including codes,\nenforcement, and rewards and punishment).\n8\nTrevin˜o( 1986) introduces a ‘person-situation interaction-\nist’ model of ethical decision making. Her model begins by\nsuggesting that the manner by which an ethical dilemma is\nanalyzed by the decision maker depends upon the individual’s\nstage of cognitive moral development (Kohlberg 1973).\n9 The\ndecision maker’s initial cognition of right and wrong is then\nmoderated by individual factors including ego strength\n(strength of conviction or self-regulating skills), ﬁeld depen-\ndence (dependence on external social referents), and locus of\ncontrol (perception of how much control one exerts over the\nevents in life). Situational factors also moderate behavior such\nas immediate job context (reinforcement contingencies such\nas rewards and punishment for ethical/unethical behavior) and\nother external pressures (including personal costs, scarce\nresources, or competition). Organizational culture (normative\nstructure, referent others, obedience to authority, and\nresponsibility for consequences) and characteristics of the\nwork also moderate behavior.\nPossibly the most signiﬁcant or prominent rationalist-\nbased theoretical model of EDM is by Rest ( 1986), who\nposited that there are four distinct process components (or\nstages) of EDM: (1) becoming aware that there is a moral\nissue or ethical problem or that the situation has ethical\nimplications (also referred to as ‘interpreting the situation,’\n‘sensitivity,’ or ‘recognition’)\n10; (2) leading to a moral\njudgment (also referred to as ‘moral evaluation,’ ‘moral\nreasoning,’ or as ‘ethical decision making’) 11; (3) estab-\nlishing a moral intent (also referred to as moral ‘motiva-\ntion,’ ‘decision,’ or ‘determination’)12; and (4) then acting\non these intentions through one’s behavior (also referred to\nas ‘implementation’ or ‘action’). 13 The moral judgment\nstage of Rest’s model which is the key moral reasoning\ncomponent of the EDM process is based on Kohlberg’s\n(1973) rationalist theory of moral development.\nJones ( 1991) provided an important contribution to\nEDM theory by not only building on and consolidating\nprevious theoretical EDM models such as Rest ( 1986), but\nby including an important new factor, the nature of the\n8 Ferrell et al. ( 1989) later suggest a revised ‘synthesis model’ which\nincorporates into their original model (1985) Kohlberg’s stages of\nmoral development as well as the deontological and teleological\nmoral evaluation process taken from Hunt and Vitells’ EDM model\n(1986).\n9 Kohlberg ( 1973) proposed three general levels of moral develop-\nment including the pre-conventional (stage one: punishment; stage\ntwo: self-interest), conventional (stage three: referent others; stage\nfour: law), and post-conventional (stage ﬁve: social contract; stage\nFootnote 9 continued\nsix: universal ethical principles). Kohlberg in later years indicated\nthat his model focused on moral reasoning, and later clariﬁed that it\nreally only focused on justice/fairness issues. See Rest et al. ( 1999).\n10 For ‘heightened ethical concern,’ see De Cremer et al. ( 2010, p. 3).\nMoral awareness is deﬁned by Rest ( 1986, p. 3) as the ‘ ‘ …interpre-\ntation of the particular situation in terms of what actions (are)\npossible, who (including oneself) would be affected by each course of\naction, and how the interested parties would regard such effects on\ntheir welfare.’’\n11 Moral judgment is deﬁned by Rest as: ‘‘[F]iguring out what one\nought to do. Applying moral ideals to the situation to determine the\nmoral course of action’ ’ (Rest 1984, p. 26).\n12 For ‘determination’ see Ferrell et al. ( 1989, p. 60). Moral intention\nmight be considered synonymous with moral motivation which Rest\ndeﬁnes as giving ‘ ‘ …priority to moral values above other personal\nvalues such that a decision is made to intend to do what is morally\nright’’ (1986, p. 3).\n13 Moral action is deﬁned as having ‘‘ …sufﬁcient perseverance, ego\nstrength, and implementation skills to be able to follow through on\nhis/her intention to behave morally, to withstand fatigue and ﬂagging\nwill, and to overcome obstacles’’ (Rest 1986, pp. 4–5).\n758 M. S. Schwartz\n123\n\nethical issue itself. Jones ( 1991, p. 367) states that an ethical\nissue exists when a person’s actions, when freely performed\n(i.e., involve a choice) ‘ ‘ …may harm or beneﬁt others.’’\nJones deﬁnes the ‘moral intensity’ of the ethical issue as a\nconstruct that ‘ ‘…captures the extent of [the] issue-related\nmoral imperative in a situation’ ’ ( 1991, p. 372). Jones’\ncomponents or characteristics of ‘moral intensity’ include:\nconsequences (i.e., magnitude of consequences, probability\nof effect, temporal immediacy, and concentration of effect);\nsocial consensus that a proposed act is evil or good; and the\nproximity or ‘the feeling of nearness’ (social, cultural, psy-\nchological, or physical) the agent has to those affected. The\nmoral intensity of the issue is proposed by Jones to inﬂuence\neach of the four stages of EDM and can act as both an\nindependent and moderating variable.\nMost other rationalist models proposed since 1991\nappear to be a variation or a combination of Rest ( 1986)\nand Jones ( 1991).\n14 Sonenshein ( 2007) groups the\nrationalist approaches into what he considers to be three\n‘prominent streams of research’: (i) manager as philoso-\npher (e.g., Hunt and Vitell 1986); (b) person-situation\n(Trevin˜o 1986); and (iii) issue-contingent (Jones 1991).\nWhat unites all of these theoretical models however is the\nemphasis on the rational cognitive process used by decision\nmakers to resolve ethical dilemmas. While rationalist\napproaches tend to recognize that intuition or emotion\nmight play a role in EDM,\n15 they would never be deter-\nminative of one’s moral judgments. Rationalist approaches\nare now beginning to recognize their limitations however,\nincluding constraints such as ‘bounded rationality’ (or\nmore speciﬁcally ‘bounded ethicality,’\n16 see Chugh et al.\n2005), or due to other cognitive biases that affect how\ninformation is processed (Messick and Bazerman 1996;\nTrevin˜o et al. 2006).17\nNon-rationalist (Intuitionist/Sentimentalist)\nApproaches\nAnother stream of EDM research has developed that argues\nthat a non-rationalist approach involving intuition (a cog-\nnitive process) and/or emotion or sentiments (an affective\nprocess) should be considered more central or ‘sovereign’\nto the moral judgment process of EDM (Saltzstein and\nKasachkoff 2004, p. 274). For example, ‘‘ …recent work in\nmoral psychology shows that ethical decisions are fre-\nquently informed by one’s feelings and intuitions’’ (Ruedy\net al. 2013, p. 532).\nIn terms of intuition, this non-rationalist research stream\nposits that intuitive (i.e., gut sense) and emotive processes\n(i.e., gut feelings) tend to at least initially generate moral\njudgments. For example, according to Haidt ( 2001): ‘‘The\ncentral claim of the social intuitionist model is that moral\njudgment is caused by quick moral intuitions and is fol-\nlowed (when needed) by slow, ex post facto moral rea-\nsoning’’ (Haidt2001, p. 818). Haidt states ( 2001, p. 814):\nIntuitionism in philosophy refers to the view that there\nare moral truths and that when people grasp these\ntruths they do so not by a process or ratiocination and\nreﬂection but rather by a process more akin to per-\nception, in which one ‘just sees without argument that\nthey are and must be true’ …Intuitionist approaches in\nmoral psychology, by extension, say that moral intu-\nitions (including moral emotions) come ﬁrst and\ndirectly cause moral judgments …Moral intuition is a\nkind of cognition, but it is not a kind of reasoning.\n18\n14 For example, other rationalist models include the ‘general theory\nmodel’ proposed by Hunt and Vitell ( 1986), a ‘behavior model’\nproposed by Bommer et al. ( 1987), and a ‘reasoned action’ model\nproposed by Dubinsky and Loken ( 1989) based on the theory of\nreasoned action (Fishbein and Ajzen 1975). In conducting a summary\nof various early models, Brady and Hatch ( 1992) propose that at least\nfour of the models (Ferrell and Gresham 1985; Hunt and Vitell 1986;\nTrevin˜o 1986; Bommer et al. 1987) contain the same four elements\n(1) a decision process, modiﬁed by (2) internal and (3) external\nfactors, leading to (4) ethical or unethical behavior.\n15 For example, Rest himself refers to the cognitive–affective\ninteractions that take place during each of the four stages of EDM\n(Rest 1984, p. 27). According to Rest ( 1986, p. 6), the moral\nawareness stage involves trying to understand our own ‘gut feelings’\nand in terms of the moral judgment stage ‘‘ …most people seem to\nhave at least intuitions about what’s morally right or wrong’’ ( 1986,\np. 8). Rest states: ‘‘ …there are different affect and cognition\ninteractions in every component’’ ( 1984, p. 28). He also states:\n‘‘…I take the view that there are no moral cognitions completely\ndevoid of affect, no moral affects completely devoid of cognitions,\nand no moral behavior separable from the cognitions and affects that\nprompt the behavior’’ (Rest 1986, p. 4). Hunt and Vitell ( 1986, p. 10)\nalso refer to the ‘feeling of guilt’ one might experience if behavior\nand intentions are inconsistent with one’s ethical judgments.\n16 ‘Bounded ethicality’ can be deﬁned as one making decisions that\nrun counter to values or principles without being aware of it (Chugh\net al. 2005; Palazzo et al. 2012).\n17 In terms of cognitive biases, Messick and Bazerman ( 1996)\npropose a series of theories about the world, other people, and\nourselves which are suggested to help explain the often unethical\ndecisions that executives make. In terms of theories about the world,\npeople often ignore possible outcomes or consequences due to ﬁve\nbiases: ‘ ‘…ignoring low-probability events, limiting the search for\nstakeholders, ignoring the possibility that the public will ‘ﬁnd out,’\ndiscounting the future, and undervaluing collective outcomes’’ ( 1996,\np. 10).\n18 Moral reasoning might also be argued to potentially take place\nwithout a conscious, effortful deliberation, suggesting it can be\nclassiﬁed as a form of intuition. Intuition might also be classiﬁed as a\nvery basic form of moral reasoning, meaning there is no real dispute\nbetween the two forms of processing, but rather they merely represent\na difference in degree (i.e., time or effort) of processing. However,\nbecause moral reasoning involves non-automatic inferential process-\ning, moral reasoning can be distinguished from intuition not only in\nterms of degree but also in terms of the kind of processing taking\nplace (see Wright 2005, pp. 28–29 and 44–45).\nEthical Decision-Making Theory: An Integrated Approach 759\n123\n\nIn other words, ‘‘ …moral reasoning is retroactive: It\nseeks to rationalize previous judgments and not to arrive at\nthose judgments’’ (Saltzstein and Kasachkoff 2004,\np. 276). One way to express the intuitive process is by\nsaying: ‘‘I don’t know, I can’t explain it, I just know it’s\nwrong’’ (Haidt2001, p. 814).\nEmotion or sentiment, deﬁned as one’s ‘feeling state’\n(Gaudine and Thorne 2001, p. 176), has also become more\nexplicitly incorporated into EDM research: ‘‘ …[C]umula-\ntive evidence from empirical research supports the asser-\ntion that ethical decision making is based not only on\nintuitive but also on emotion-based mechanisms, and that\nemotions constitute a key component of moral decision\nmaking’’ (Salvador and Folger 2009, pp. 11–12). Tangney\net al. ( 2007, p. 346) also note the importance of emotion in\nrelation to EDM: ‘‘Moral emotions may be critically\nimportant in understanding people’s behavioral adherence\n(or lack of adherence) to their moral standards.’’ Emotions\nthat have been suggested as being more directly related to\nEDM can be categorized into: (i) ‘pro-social’ emotions\nwhich promote morally good behavior such as empathy,\nsympathy, concern, or compassion\n19; (ii) ‘self-blame’\nemotions such as guilt and shame; or (iii) or ‘other-blame’\nemotions, such as contempt, anger, and disgust (see Prinz\nand Nichols 2010).\n20\nSeveral researchers have attempted to explain how\nemotion impacts EDM. Haidt ( 2001) as a non-rationalist\nappears to directly link emotion to intuition with little\nemphasis placed on reason. According to Elfenbein ( 2007,\np. 348): ‘‘The three main perspectives on the relationship\nbetween emotion and cognition are that emotion interferes\nwith cognition, that emotion serves cognition, and that the\ntwo are intertwined …’’ Greene et al. ( 2001) link emotions\ndirectly to the cognitive process and state (p. 2107):\n‘‘…emotional responses generated by the moral-personal\ndilemmas have an inﬂuence on and are not merely inci-\ndental to moral judgment.’’\n21 According to Damasio\n(1994), emotion is not in conﬂict with reason but provides\ncrucial support to the reasoning process by acting as a\nregulator of conduct. Another similar means to explain the\nrelationship between emotion and reason is by describing\nemotions as the ‘hot system’ (‘go’), which can undermine\nefforts to self-control one’s behavior. In contrast, the ‘cool\nsystem’ (‘know’) which is cognitive, contemplative, and\nemotionally neutral can potentially control the ‘hot system’\nthrough what is referred to as ‘moral willpower’ (Metcalfe\nand Mischel 1999).\n22\nThe non-rationalist approaches have been persuasively\nargued by researchers such as Haidt ( 2001) and Sonenshein\n(2007). Building on the works of philosophers like\nShaftesbury and Hume, Haidt ( 2001, p. 816) suggests that:\n‘‘…people have a built-in moral sense that creates plea-\nsurable feelings of approval toward benevolent acts and\ncorresponding feelings of disapproval toward evil and\nvice.’’ The relationship between emotions and intuition is\nnot so clear however. Monin et al. ( 2007, p. 101) state that:\n‘‘The difference between intuitions and emotions …seems\nto be that intuitions are behavioral guides or evaluations\nthat directly follow from an emotional experience.’’ Dane\nand Pratt ( 2007, pp. 38–39) refer to intuitive judgments as\n‘‘…affectively charged, given that such judgments often\ninvolve emotions’’ and are ‘‘…detached from rationality.’’\nKahneman ( 2003) states: ‘‘The operations of [intuition] are\ntypically fast, automatic, effortless, associative, implicit\n(not available to introspection), and often emotionally\ncharged.’’ This seems to suggest that emotions either affect\nor cause intuitions and are thus importantly related, or in\nother cases, emotions may directly affect any of the four\nEDM stages (Gaudine and Thorne 2001). It is important to\nnote however that not all intuitive judgments are neces-\nsarily emotionally charged, and that intuitions should be\nconsidered to be a cognitive (albeit non-deliberate) process\nevoked by the situation: ‘‘It must be stressed …that intu-\nition, reasoning, and the appraisals contained in emo-\ntions…are all forms of cognition’’ (Haidt 2001, p. 818).\nProposed Reformulation: Integrated Ethical\nDecision-Making (I-EDM) Model\nBuilding on previous EDM models and in order to address\nthe key divergence outlined above between the rationalist\nand non-rationalist approaches to EDM, a reformulated and\nmore integrative EDM model, referred to as ‘Integrated\nEthical Decision Making’ (or I-EDM), will now be\ndescribed (see Fig. 1 below).\nAt its most basic level, there are two major components\nto the I-EDM model: (1) the EDM process (including\n19 While positive emotions such as empathy are generally associated\nwith ethical behavior, it may also be the case that positive affect arises\nfollowing unethical behavior (e.g., cheating) which can then reinforce\nadditional future unethical behavior. See: Ruedy et al. ( 2013).\n20 The sorts of emotions that have been suggested as impacting EDM\ninclude anger; anxiety; compassion; distress; dominance; embarrass-\nment; empathy; fear; grief; guilt; hope; humiliation; love; meaning-\nlessness; mercy; pride; regret; remorse; responsibility; sadness;\nshame; and sympathy (see: Haidt 2001; Agnihotri et al. 2012).\nEisenberg ( 2000) provides a review of the research on guilt, shame,\nempathy, and moods in relation to morality.\n21 ‘Moral-personal’ dilemmas (as opposed to ‘impersonal’ dilemmas)\nthat trigger an emotional response relate to situations such as deciding\nwhether to physically push someone onto a trolley track to save the\nlives of many others. See Greene et al. ( 2001).\n22 Moral willpower (or self-sanction) can act like a ‘moral muscle’\nthat can be depleted following heavy use, or strengthened over time\n(see Muraven et al. 1999).\n760 M. S. Schwartz\n123\n\nantecedents and subsequents along with lack of moral\nawareness); and (2) the factors (or variables) that inﬂuence\nthe EDM process. The EDM process is composed of four\nbasic stages: (i) awareness; (ii) judgment; (iii) intention;\nand (iv) action/behavior, and in this respect continues to\nreﬂect the basic process framework proposed by Rest\n(1984, 1986). The antecedents to the EDM process include\nbasic environmental norms, while the subsequent stages of\nthe process include potential learning feedback loops . The\nEDM factors that inﬂuence the process fall into two basic\ncategories: (i) individual; and (ii) situational (Trevin˜o\n1986). The I-EDM model assumes that ethical behavior is\ncontingent on which particular individual is facing the\nethical dilemma (e.g., different individuals may act dif-\nferently when faced with the same dilemma), and (ii) the\nsituational context within which an individual faces a\ndilemma (e.g., the same individual can behave differently\ndepending on the particular situation one is facing or\nenvironment one is situated within). The following will\nﬁrst describe the individual and situational factors that can\ninﬂuence each of the stages of EDM, followed by a\ndescription of each stage in the Integrated-EDM process.\nIndividual Factors\nMost EDM models refer to individual factors or variables\nincluding, for example, ego strength, ﬁeld dependence, and\nlocus of control (Trevin ˜o 1986), values (Ferrell and Gre-\nsham 1985), or personal experiences (Hunt and Vitell\n1986). It may however be more useful to utilize a broader\nconstruct that captures all of the individual factors. Toward\nthis end, the I-EDM model attempts to collate together all\nthe individual factors into one general overarching main\nconstruct: one’s ‘moral capacity ’ (see Hannah et al. 2011).\nThere are two inter-related but distinct components that\ncomprise an individual’s moral capacity: (i) moral char-\nacter disposition ; and (ii) integrity capacity . Moral\ncapacity is deﬁned as the ability of an individual to avoid\nmoral temptations, engage in the proper resolution of eth-\nical dilemmas, and ultimately engage in ethical behavior.\nIn other words, one’s moral capacity is based not only on\none’s level of moral maturity and the core ethical values\nthey possess, but the extent to which they will cling to\nthose values even when faced with pressures to act other-\nwise. Each component of moral capacity will now be\ndescribed in more detail.\nThe ﬁrst component of an individual’s moral capacity is\none’smoral character disposition . A number of researchers\nhave raised the concern that this factor is lacking in EDM\nmodels. According to Pimental et al. ( 2010, p. 360): ‘‘The\npresently available models are insufﬁcient [because] they\nfail to ﬁnd that individuals’ characteristics are integral to\nthe identiﬁcation of ethical dilemmas.’’ Others suggest that\n‘‘…‘bad’ or ‘good’ apples, or bad features of otherwise\ngood apples play a role in decision making as well’’\n(Watson et al. 2009, p .12). Damon and Hart ( 1992, p. 455)\npropose that: ‘‘ …there are both theoretical and empirical\nreasons to believe that the centrality of morality to self may\nAwareness\n(Recognize)\nConsulta/g415on\n(Conﬁrm)\nIssue\nNorms\nLearning\n(Retrospect)\nEmo/g415on\n(Feel)\nRa/g415onaliza/g415on\n(Jus/g415fy)\nReason\n(Reﬂect)\nIntui/g415on\n(Sense)\nJudgment\n(Evaluate)\nInten/g415on\n(Commit)\nBehavior\n(Act)\nLackof\nAwareness\n(Overlook)\nSitua/g415on\n(Issue;Organiza/g415on;\nPersonal)\nIndividual\n(MoralCapacity)\nModera/g415ng\nFactors\nFig. 1 Integrated ethical decision-making model. Primary sources of\nthe model: Rest ( 1984, 1986) (four-component model); Jones ( 1991)\n(issue-contingency model); Trevin˜o( 1986) (person–situation interac-\ntionist model); Tenbrunsel and Smith-Crowe ( 2008) (lack of moral\nawareness); Hannah et al. ( 2011) (moral capacity); Haidt ( 2001)\n(social intuitionist model). Legend solid box—mental state; dotted\nbox—mental process; solid circle—active conduct; dotted circle—\nfactor/variable\nEthical Decision-Making Theory: An Integrated Approach 761\n123\n\nbe the single most powerful determiner of concordance\nbetween moral judgment and conduct.’’ It is therefore clear\nthat moral character disposition should be incorporated into\nany EDM model.\nWhile there might be several different approaches to\ndeﬁning moral character disposition, 23 for the purposes of\nthe Integrated-EDM model, it is intended to be a broad\nconstruct that would potentially capture other moral char-\nacter concepts that have been identiﬁed in the EDM liter-\nature. These concepts include ‘cognitive stage of moral\ndevelopment’ (CMD) (Kohlberg 1973; Trevin˜o 1986),\n‘current ethical value system’\n24 (CEVS) (Jackson et al.\n2013), ‘personal value orientations’ (Weber 1993; Bartlett\n2003), ‘philosophy/value orientation’ (O’Fallon and But-\nterﬁeld 2005), ‘ethical ideology’ 25 (Schlenker 2008),\n‘ethical predisposition’ (Brady and Wheeler 1996; Rey-\nnolds 2006b26), and ‘moral sensitivity’ (Reynolds 2008).\nMoral character disposition is closely related to the con-\nstruct of ‘moral maturation’ described by Hannah et al.\n(2011, pp. 669–670) which includes moral ‘complexity’\n(i.e., ‘‘knowledge of concepts of morality’’), ‘meta-cogni-\ntive ability’ (i.e., the ‘engine’ used to ‘‘deeply process\ncomplex moral knowledge’’), and ‘moral identity’\n27 (i.e.,\n‘‘….individuals’ knowledge about themselves as moral\nactors’’). For the purposes of the I-EDM model, an indi-\nvidual’s moral character disposition is deﬁned as one’s\nlevel of moral maturity based on their ethical value system,\nstage of moral development, and sense of moral identity.\nMoral capacity however also includes another construct\nrelated not just to one’s moral character disposition but to\nthe commitment or motivation one has to act consistently\naccording to their moral character disposition through their\nability to self-regulate (see Jackson et al. 2013). The con-\nstruct that comes closest to capturing this consistency and\ntherefore what will be used in the I-EDM model is one’s\nintegrity capacity suggested by Petrick and Quinn ( 2000).\nThey deﬁne ‘integrity capacity’ as the individual’s\n‘‘…capability for repeated process alignment of moral\nawareness, deliberation, character and conduct …’’ (2000,\np. 4).\nThe construct of integrity capacity overlaps closely with\nRest’s ( 1986) conceptualization of ‘moral character’ or\nHannah et al.’s ( 2011) ‘moral conation’ construct (i.e., the\nimpetus or moral willpower to act in accordance with one’s\nethical values or principles). Integrity capacity would\ninclude concepts such as ‘moral ownership’ (i.e., the extent\nto which one feels responsible over the ethical nature of their\nown actions or the actions of others), ‘moral efﬁcacy’ (i.e.,\nbelieving one has the capability to act ethically), and ‘moral\ncourage’ (i.e., the strength and commitment to resist pres-\nsures to act unethically) (see Hannah et al. 2011). An indi-\nvidual’s moral capacity is continuously tested depending on\nthe circumstances one is facing. Whether one’s moral\ncharacter disposition will be maintained when put to the test\ndepends directly on one’s integrity capacity, meaning there\nis a direct relationship between the two constructs.\nAccording to the I-EDM model, rather than directly\naffecting awareness, judgment, intention, or behavior as\nsuggested in much EDM research, the key EDM individual\nvariables found in EDM literature potentially affect one’s\n‘moral capacity’ which then potentially affects the various\nEDM stages. These include demographic variables (e.g.,\nage, gender, education, nationality, work experience, etc.),\npersonality or psychological variables (e.g., cognitive\nmoral development/CMD, locus of control, ego strength,\netc.), and variables more directly related to one’s ethical\nexperience (e.g., religion/religiosity, ethics training, pro-\nfessional education, etc.).\n28 Figure 2 below depicts the\nindividual moral capacity construct.\nSituational Context\nAs indicated above, all dominant EDM models refer to\nsituational or organizational factors that can impact the\ndecision-making process (Bommer et al. 1987; Ferrell and\nGresham 1985; Hunt and Vitell 1986; Trevin˜o 1986).\nBuilding on these models along with Jones ( 1991), the\n23 For example, one might include intuition and emotions (or the\nability to control one’s emotions) as part and parcel of one’s moral\ncharacter based on a virtue-based ethics approach. For the purposes of\nthe I-EDM model, intuition and emotion are described as part of the\nmoral judgment stage; however, the extent and manner in which this\ntakes place would potentially depend on one’s moral character\ndisposition.\n24 ‘Current ethical value system’ (CEVS) is the framework that\nguides an individual’s ethical choices and behavior (see Jackson et al.\n2013, p. 236).\n25 Ethical ideology is ‘‘ …an integrated system of beliefs, values,\nstandards, and self-assessments that deﬁne an individual’s orientation\ntoward matters of right and wrong’’ (McFerran et al. 2010, p. 35).\nOne’s ‘ethical ideology’ is made up of one’s ‘moral personality’ and\n‘moral identity’ (McFerran et al. 2010). Schlenker ( 2008, p. 1079)\nsuggests that there is a continuum between a ‘principled ideology’\n(one believes moral principles exist and should guide conduct\n‘‘…regardless of personal consequences or self-serving rationaliza-\ntions’’) and ‘expedient ideology’ (one believes moral principles have\nﬂexibility and that deviations for personal gain are justiﬁable).\n26 Ethical predisposition is deﬁned as ‘‘ …the cognitive frameworks\nindividuals prefer to use in moral decision making’’ (Reynolds 2006b,\np. 234).\n27 ‘Moral identity’ has been suggested by several theorists as playing\nan important self-regulatory role in linking moral attitudes to one’s\nbehavior. See Schlenker ( 2008, p. 1081). See also Lapsley and\nNarvaez ( 2004) for a review of the concept of moral identity.\n28 See O’Fallon and Butterﬁeld ( 2005) and Craft ( 2013) for a\ncomplete list of EDM individual-related variables that would\npotentially fall into these categories.\n762 M. S. Schwartz\n123\n\nsituational context of the I-EDM model comprises three\ncomponents: (1) the issue; (2) the organizational infras-\ntructure; and (3) personal factors.\nIssue\nWith respect to the ﬁrst component, rather than focusing on\nthe good or bad ‘apples’ (i.e., individual characteristics) or\nthe good or bad ‘barrels’ (i.e., organizational environment),\nsome have argued that the issue itself should be the focus of\nEDM (Jones 1991;W e b e r 1996; Bartlett 2003;K i s h -\nGephart et al. 2010). While Jones’ ( 1991) issue-contingent\nmodel clearly moved EDM in this direction, it is not clear if\nit was moved far enough in certain respects. For the pur-\nposes of the I-EDM model, the issue variable would consist\nof three dimensions: (i) issue moral intensity; (ii) issue\nimportance; and (iii) issue complexity. Each dimension of\nthe issue-related variable will now be described.\nAs indicated above, Jones ( 1991) suggests that the moral\nintensity of an issue can impact each of the four stages of the\nEDM process. One initial concern with Jones’ moral inten-\nsity construct is that the dimensions of moral intensity can\nsimply be incorporated into the moral judgment stage\n(Herndon 1996).\n29 Setting this concern aside, Jones’ char-\nacteristics of moral intensity can also be considered some-\nwhat limited in a normative sense. Jones only considers\nconsequences (either positive or negative), social norms, and\nthe proximity or ‘closeness’ the agent has to those affected,\nas tied to moral intensity. For the purposes of the I-EDM\nmodel, the moral intensity of an issue would include not only\nJones’ ( 1991) criteria, but would be extended to include\nadditional deontological (i.e., duty-based) and fairness\ndimensions (see May and Pauli 2002; McMahon and Harvey\n2007; Singer 1996). In other words, the moral intensity of an\nissue would be expected to increase if an individual is facing\na situation which might require breaking rules (e.g., codes),\nlaws, or promises, acting in a disloyal or dishonest manner,\ninfringing the moral rights of others, or relate to notions of\nretributive, compensatory, procedural, or distributive justice.\nAs indicated by some researchers, ‘ ‘ …other ethical per-\nspectives should also be considered …such as fairness or law\nbreaking where harm was not involved’ ’ as part of the moral\nintensity construct (Butterﬁeld et al. 2000, p. 1010). A higher\nlevel of moral intensity would then presumably increase the\nlikelihood of moral awareness (see May and Pauli 2002).\nIssue importance is another component that would be\ntaken into account by the I-EDM model. Issue importance is\ndeﬁned as the ‘‘ …perceived personal relevance or impor-\ntance of an ethical issue to an individual’’ (Robin et al. 1996,\np. 17, emphasis added). A number of researchers have shifted\nJones’ (1991) focus on the moral intensity of an issue to the\nsubjective importance placed on a particular issue by a par-\nticular individual. The reason for this approach is that any\nobjective determination of issue intensity would be irrele-\nvant unless the decision maker himself or herself subjec-\ntively perceived the issue as being of importance (Haines\net al. 2008; Valentine and Hollingworth 2012;Y u 2015;\nDedeke 2015). If issue importance to the decision maker is\nnot considered, the ethical implications of the issue might be\nignored altogether leading to a lack of moral awareness.\nAnother dimension of an issue that appears to have been\nignored in EDM theoretical models is the extent to which an\nissue is perceived to be very complex. Issue complexity is\ndeﬁned as issues that are perceived by the decision maker to\nbe hard to understand or difﬁcult to resolve. Warren and\nSmith-Crowe ( 2008, p. 90) refer to issue complexity in\nrelation to the type of moral judgment (reason versus intu-\nition) that might take place: ‘‘ …the intuitionists are not\nseeking judgments from individuals on issues that are new,\ncomplex, or have many options.’’ Issue complexity can\ninvolve the perceived degree of conﬂict among competing\nmoral standards or multiple stakeholder claims. Issues can\nalso be perceived as more complex when the decision maker\nhas never faced a similar situation before, or faces a wide\nrange of different alternatives. Issue complexity might also\ninclude other components such as the degree to which there\nare complicated facts involved or multiple factual assump-\ntions that need to be made due to a lack of relevant infor-\nmation being available. Such information may be necessary\nin order to properly understand the ramiﬁcations of a par-\nticular issue (e.g., potential future harm to oneself or others).\nIn a similar vein, relevant knowledge on the issue has been\nsuggested as being linked with ‘‘…one’s ability to engage in\neffortful cognitive activity’’ (see Street et al. 2001, p. 263).\nAs a result, regardless of its intensity or importance, the mere\nperceived complexity of the issue or dilemma could possibly\ncause one to ignore facing and addressing the issue alto-\ngether, leading to a type of ‘moral paralysis.’ For example,\ndeciding whether to blow the whistle on ﬁrm misconduct can\nbe a highly complex and difﬁcult decision with ramiﬁcations\nto multiple parties (De George 2010) which might prevent\nMoral Character \nDisposition Integrity Capacity \nIndividual Moral Capacity\nDemographics Ethical\nExperience\nPersonality/\nPsychological\nFig. 2 Individual moral capacity\n29 For example, Herndon states ( 1996, p. 504): ‘‘While Jones ( 1991)\nadds the concept of moral intensity which is the degree of ‘badness’\nof an act; it can be placed in the consequences and behavioral\nevaluation portions of the synthesis integrated model.’’\nEthical Decision-Making Theory: An Integrated Approach 763\n123\n\ncoming to any judgment on the ethically appropriate action\nto take. Due to its potential impact on at least the moral\nawareness and moral judgment stages, perceived ‘issue\ncomplexity’ is also included in the I-EDM model as part of\nthe issue-related situational construct in addition to issue\nintensity and issue importance.\nOrganizational Environment\nThe second component of the situational context is the\norganizational environment. One potentially useful way to\ndenote organizational factors is to collectively refer to them\nas representing the ‘ethical infrastructure’ of the organi-\nzation (Tenbrunsel et al. 2003; Trevin˜o et al. 2006). Ethical\ninfrastructure, as the overarching construct for all organi-\nzational environmental variables, is deﬁned as ‘‘ …the\norganizational elements that contribute to an organization’s\nethical effectiveness’’ (Tenbrunsel et al. 2003, p. 286). The\nethical infrastructure would include formal and informal\nsystems such as communication systems (i.e., codes of\nconduct or ethics, missions, performance standards, and\ncompliance or ethics training programs), surveillance sys-\ntems (i.e., performance appraisal and reporting hotlines),\nand sanctioning systems (i.e., rewards and punishments\nincluding evaluations, promotions, salary, and bonuses).\n30\nBoth the formal and informal systems form part of ‘‘ …the\norganizational climates that support the infrastructure’’\n(Tenbrunsel et al. 2003, p. 286). A substantial body of\nempirical research has examined the potential impact the\nvarious components of ethical infrastructure can have on\nethical decision making by individuals within organiza-\ntions (see O’Fallon and Butterﬁeld 2005; Craft 2013). The\nunderlying assumption is that ﬁrms with a strong ethical\nculture and climate generally lead to more employees\nbecoming aware of ethical issues and the importance of\nbehaving in what would be considered by the company to\nbe in an ethical manner (Ethics Resource Center 2014).\nThe impact of signiﬁcant or ‘referent’ others/peers\nwhich can lead to one imitating or learning from the\nbehavior of others along with authority pressures (e.g.,\nmanagers or executives) would also be included in the\nI-EDM model as part of the ethical infrastructure (e.g.,\nHunt and Vitell 1986; Bommer et al. 1987; Trevin˜o 1986).\nOpportunity, or ‘‘ …the occurrence of circumstances to\npermit ethical/unethical behavior’’ would also be included\nas a component of an organization’s ethical infrastructure\nin terms of organizational culture (Ferrell et al. 1989,\np. 61).\nPersonal Situation\nOne’s personal situation, as distinct from one’s moral\ncapacity, is the ﬁnal component of the situational context.\nThe key variable of one’s personal situation is one’s per-\nceived ‘need for personal gain,’ which can result from\nliving beyond one’s means, high debt, ﬁnancial losses, or\nunexpected ﬁnancial needs (see Albrecht 2003). Another\nmeans of expressing one’s ‘need for personal gain’ at any\ngiven point in time is what might be referred to as one’s\ncurrent state of ‘ethical vulnerability.’\n31 This means that if\none is in a weak ﬁnancial position, facing signiﬁcant per-\nceived ﬁnancial pressures or obligations, with few or non-\nexistent career or job alternatives available, one would\npresumably be in a much weaker position to resist uneth-\nical requests and put one’s job, promotion, or bonus at risk\nor be willing to accept the ‘personal costs’ of taking moral\naction (Trevin˜o 1986). Other constraints such as time\npressure or limited ﬁnancial resources to do what one\nknows to be right can also be considered part of the per-\nsonal situational context (Trevin ˜o 1986).\nOne or more of the situational factors can come into\ndirect conﬂict with one’s moral character disposition, and\nwhether one is able to withstand the pressures one faces\nwould be dependent on the extent of one’s integrity\ncapacity. Figure 3 below depicts each of the components of\nthe situational context construct.\nProcess Stages of EDM\nNow that the individual and situational context factors have\nbeen described, the process stages of the I-EDM model\nwhich can be affected by the moderating variables can be\noutlined. In terms of the process of the I-EDM model, the\ninitial starting point are the norms (i.e., environment) that\nare prevalent which tend to determine whether an ethical\nissue or dilemma potentially exists. Norms are deﬁned as\nthose prevailing standards or expectations of behavior held\nby members of a particular group or community. Norms\ncan simultaneously exist at several different levels,\nincluding at the societal/cultural/national level (e.g., brib-\nery is seen as being generally acceptable), at the organi-\nzational level\n32 (e.g., dating a work colleague is considered\nunacceptable according to corporate policy), or at the work\ngroup level (e.g., padding expense accounts is viewed as\nacceptable by one’s work colleagues).\n30 As an alternative to ‘ethical infrastructure,’ others (e.g., Valentine\net al. 2013) have used the term ‘ethical context’ to refer to both the\n‘ethical culture’ (Trevin˜o et al. 1998) and the ‘ethical climate’ of the\norganization (Victor and Cullen 1988).\n31 The notion of ‘vulnerability’ has apparently received little\nattention in the business ethics literature. See: Brown ( 2013).\n32 The ﬁrm’s ethical infrastructure should be considered distinct from\norganizational-level norms, although there would clearly be a\nrelationship between them. This discussion is however beyond the\nscope of the paper.\n764 M. S. Schwartz\n123\n\nSeveral EDM models propose that there is an ‘environ-\nmental’ context within which the existence of an ethical\nissue or dilemma can arise (Ferrell and Gresham 1985; Hunt\nand Vitell 1986; Jones 1991; Brass et al. 1998; Randall\n1989; Trevin˜o 1986). While the sources of these norms\nmight also be discussed, such as deeply embedded socio-\nlogical, political, legal, or religious considerations or views,\nthis discussion is beyond the scope for the purposes of this\npaper. For the I-EDM model, a potential ethical issue or\ndilemma arises when there is a situation whereby different\nnorms apply, each of which cannot be followed at the same\ntime. This basic starting point of the EDM process has also\nbeen referred to as the ‘eliciting situation’ (Haidt 2001).\nMoral Awareness\nAssuming that a situation with a potential ethical issue or\ndilemma exists due to conﬂicting norms, the next question\nis whether the individual becomes aware of the existence of\nthe issue or dilemma. Moral awareness is deﬁned as the\npoint in time when an individual realizes that they are\nfaced with a situation requiring a decision or action that\ncould the affect the interests, welfare, or expectations of\noneself or others in a manner that may conﬂict with one or\nmore moral standards (Butterﬁeld et al. 2000). Moral\nawareness that a particular situation raises ethical issues\ncan take place simply due to an individual’s moral capacity\nand inherent ability to recognize ethical issues (Hannah\net al. 2011) and/or as a result of a ﬁrm’s ethical infras-\ntructure (i.e., including codes, training, meetings, or other\ndisseminated ethical policy communications) (Tenbrunsel\net al. 2003). If one becomes aware that an ethical issue or\ndilemma exists, then one has by deﬁnition identiﬁed at\nleast two different possible courses of action, and can then\npotentially engage in an EDM process consisting of the\nmoral judgment and intention stages.\n33 The following will\nnow explain how the ‘lack of moral awareness’ process\ntakes place, considered to be an equally important com-\nponent of the I-EDM model.\nLack of Moral Awareness\nThe vast majority of EDM theoretical models, by relying\non Rest ( 1986), presume that only through moral awareness\nof the potential ethical nature of a dilemma can one ulti-\nmately engage in ethical behavior. For example, Sonen-\nshein states ( 2007, p. 1026): ‘‘ …moral awareness is often\nviewed as binary—you either recognize the ethical issue or\nyou fail to do so …Consequently, research has tended to\nfocus on whether moral awareness is present or absent as a\nprecondition for activating the other stages of rationalist\nmodels (Jones 1991,p .3 8 3 ) …’’ What appears to be lack-\ning in current EDM models however is the depiction of\none’s lack of moral awareness, meaning one does not\nrealize (i.e., they overlook) that the situation one is expe-\nriencing raises ethical considerations.\nThere are now several overlapping theories that have\nbeen proposed in EDM literature to help explain the pro-\ncesses or reasons by which one might lack moral aware-\nness, also referred to as unintentional ‘amoral awareness’\n(Tenbrunsel and Smith-Crowe 2008) or unintentional\n‘amoral management’ (Carroll 1987).\n34 For example,\nBandura’s theoretical work on moral disengagement is an\nimportant theoretical source underlying one’s lack of moral\nawareness. According to Bandura ( 1999), moral disen-\ngagement involves a process by which one convinces\noneself in a particular context that ethical standards do not\napply. Moral standards regulate behavior only when self-\nregulatory mechanisms or ‘moral self-sanctions’ (i.e., one’s\nconscience) are activated. Psychological processes that can\nprevent this activation include ‘‘ …restructuring of inhu-\nmane conduct into a benign or worthy one by moral jus-\ntiﬁcation, sanitizing language, and advantageous\ncomparison; disavowal of a sense of personal agency by\ndiffusion or displacement of responsibility; disregarding or\nminimizing the injurious effects of one’s actions; and\nIssue Organization (Ethical \nInfrastructure)\nSituational Context\nPersonal\nIntensity;\nImportance;\nComplexity\nPerceived Need \nfor Gain;\nConstraints\n(time, financial \nability)\nCommunication; \nTraining; \nSanctioning \nSystems\n(including\npeers, authority,\nopportunity, \nrewards, sanctions)\nFig. 3 Situational context for EDM\n33 There is however a risk of moral awareness being confounded with\nmoral judgment, especially when the deﬁnition of moral awareness\nFootnote 33 continued\nincludes consideration of one or more ethical standards (see Reynolds\n2006b, p. 233).\n34 Carroll ( 1987) refers to ‘amoral managers,’ who can either act\nintentionally or unintentionally. Unintentional amoral managers\n‘‘…do not think about business activity in ethical terms. These\nmanagers are simply casual about, careless about, or inattentive to the\nfact that their decisions and actions may have negative or deleterious\neffects on others. These managers lack ethical perception and moral\nawareness; that is, they blithely go through their organizational lives\nnot thinking that what they are doing has an ethical dimension to it.\nThey may be well intentioned but are either too insensitive or\negocentric to consider the impacts on others of their behavior’’\n(Carroll 1987, p. 11).\nEthical Decision-Making Theory: An Integrated Approach 765\n123\n\nattribution of blame to, and dehumanization of, those who\nare victimized’’ (Bandura 1999, p. 193).\nSimilar to moral disengagement, one can also lack moral\nawareness due to ethical fading . Ethical fading is ‘‘ …the\nprocess by which the moral colors of an ethical decision\nfade into bleached hues that are void of moral implica-\ntions’’ (Tenbrunsel and Messick 2004, p. 224). In order for\n‘ethical fading’ to take place, people engage in self-de-\nception through the use of euphemistic language (e.g.,\n‘aggressive’ accounting practices; ‘right sizing’) and other\ntechniques to ‘shield themselves’ from their own unethical\nbehavior. Another similar concept used to explain one’s\nlack of moral awareness is ethical blindness ,o r‘ ‘ …the\ndecision maker’s temporary inability to see the ethical\ndimension of a decision at stake’’ (Palazzo et al. 2012,\np. 324). Ethical blindness includes three aspects: (i) people\ndeviate from their own values and principles; (ii) this\ndeviation is temporary in nature; and (iii) the process is\nunconscious in nature (Palazzo et al. 2012, p. 325).\n35\nAnother theory related to a lack of moral awareness is\nthe use of non-moral decision frames , which occurs when\none focuses on the business or legal implications of issues\nrather than on the ethical considerations (Tenbrunsel and\nSmith-Crowe 2008; Dedeke 2015). The process of framing\nin a non-moral manner leading to a lack of awareness can\nresult due to insufﬁcient or biased information gathering, or\nsocially constructing the facts in a particular manner (So-\nnenshein 2007). Moral myopia can also take place which is\nsimilarly deﬁned as ‘‘ ….a distortion of moral vision that\nprevents moral issues from coming into focus’’ (Drum-\nwright and Murphy 2004, p. 7). These initial theories or\nprocesses (moral disengagement, ethical fading, ethical\nblindness, non-moral decision frames, and moral myopia)\nappear to relate more directly to one’s work environment\nleading to a lack of moral awareness. In other words, if one\nis situated in a work environment which tends to ignore\nethical considerations in its decision making or consistently\nprioritizes the bottom line over ethical concerns, as well as\nuses non-moral language in its operations,\n36 then one\nwould likely be less inclined to be morally aware when\nfacing a dilemma.\nMoral awareness however could be attributable to the\nparticular individual’s inherent nature, and thus directly\nrelated to one’s moral character disposition described\nabove. For example, moral awareness can result from\nmoral attentiveness , which has been deﬁned as: ‘‘ …the\nextent to which an individual chronically perceives and\nconsiders morality and moral elements in his or her expe-\nriences’’ (Reynolds2008, p. 1027). Similar to the notion of\nmoral attentiveness, others have linked moral awareness to\nthe concept of mindfulness, which is described as ‘‘ …an\nindividual’s awareness both internally (awareness of their\nown thoughts) and externally (awareness of what is hap-\npening in their environment)’’ (Ruedy and Schweitzer\n2010, p. 73). It may be that a lack of mindfulness exac-\nerbates one’s self-serving cognition, self-deception, and\nunconscious biases leading to unethical behavior: ‘‘Mindful\nindividuals may feel less compelled to ignore, explain\naway, or rationalize ideas that might be potentially\nthreatening to the self, such as a conﬂict of interest or a\npotential bias’’ (Ruedy and Schweitzer 2010, p. 76).\nEngaging in moral imagination (Werhane 1998) might\nalso potentially lead to moral awareness, while failing to\nengage in moral imagination might lead to a lack of moral\nawareness. Moral imagination involves whether one has\n‘‘…a sense of the variety of possibilities and moral con-\nsequences of their decisions, the ability to imagine a set of\npossible issues, consequences, and solutions’’ (Werhane\n1998, p. 76). When one is only able to see one option rather\nthan create imaginative solutions, one may be unaware that\none is even facing an ethical dilemma with a potentially\nmore ethical alternative being available. Figure 4 below\nsummarizes the theories or processes discussed above that\nhelp explain and contribute to moral awareness or a lack of\nmoral awareness.\nBy not including the phenomenon of ‘lack of moral\nawareness’ in EDM models, an important stream of EDM\nresearch is being ignored. Even if one is not aware that an\nethical dilemma exists, one can still engage in what might\nbe considered ‘unintentional’ ethical or unethical behavior\n(Tenbrunsel and Smith-Crowe 2008; Jackson et al. 2013).\nDue to the importance of understanding why there might be\na lack of moral awareness and the processes leading to it,\nwhich would presumably increase the potential for\nEthical \nIssue\n• Moral Disengagement\n Ethical Fading\n Ethical Blindness\n Non-Moral Framing\n Moral Myopia\n Moral Attentiveness\n Moral Mindfulness\n Moral Imagination\n Moral Framing \nMoral\nAwareness\nLack of Moral \nAwareness\nFig. 4 Processes affecting moral awareness\n35 The classic example of ‘ethical blindness’ comes from the recall\ncoordinator of the defective Ford Pinto vehicle who asked himself:\n‘‘Why didn’t I see the gravity of the problem and its ethical\novertones?’’ (Gioia1992, p. 383).\n36 This can also take place due to moral muting , which involves\nmanagers who ‘ ‘ …avoid moral expressions in their communica-\ntions…’’ (Bird and Waters 1989, p. 75).\n766 M. S. Schwartz\n123\n\nunethical behavior, the lack of moral awareness path is\ndepicted in the I-EDM model.\nMoral Judgment and Intention Stages of I-EDM\nThe moral judgment and intention stages represent the crux\nof the I-EDM model, and might be referred to as the actual\nEDM process that takes place. Moral judgment is deﬁned\nfor the purposes of the model as the determination of the\nmost ethically appropriate course of action among the\nalternatives. Moral intention is deﬁned as the commitment\nor motivation to act according to one’s moral values.\n37 This\nis the point in the I-EDM model where several different\nprocesses either affect moral judgment directly, or poten-\ntially interact with each other leading to judgment and\nintention. These mental processes include (i) emotion; (ii)\nintuition; (iii) reason; (iv) rationalization; as well as (v) the\nactive process of consultation.\nAs can be seen in Fig. 1 above, the Integrated-EDM\nmodel does not suggest that only reason or intuition is\ninvolved in the moral judgment process, but that both are\npotentially involved, along with emotion and rationaliza-\ntion. As indicated above, a growing number of researchers\nare indicating the importance of including what has been\nreferred to as the ‘dual process’ of both reason and emo-\ntion/intuition in any EDM model (e.g., see Elm and Radin\n2012; Marquardt and Hoeger 2009). For example, Woice-\nshyn ( 2011, p. 313) states [emphasis added]: ‘‘Following\nthe developments in cognitive neuroscience and neu-\nroethics (Salvador and Folger 2009) and paralleling the\ngeneral decision-making literature (Dane and Pratt 2007),\nmost researchers have since come to hold a so-called dual\nprocessing model of ethical decision making.’’\nDespite this fact, very few studies provide a clear visual\ndepiction of the inﬂuence of reason, intuition, and emotion\non EDM. Haidt ( 2001) includes reason (or reasoning) as\nwell as intuition in his schematic social intuitionist model,\nalthough as indicated above reason serves primarily a post\nhoc rationalization function and emotion (or affect) appears\nto be comingled with intuition. Reynolds ( 2006a) proposes\na two-system model which also includes both intuition (the\nreﬂexive X-system) and reason (the higher order conscious\nreasoning C-system) but appears to have left out the impact\nof emotion. Woiceshyn ( 2011) also attempts to integrate\nreason and intuition through a process she calls ‘integration\nby essentials’ and ‘spiraling’ but does not explicitly include\nemotion. Gaudine and Thorne ( 2001) visually depict the\ninﬂuence of emotion on the four EDM stages but do not\nrefer to intuition. Other ﬁelds, such as social psychology,\nhave attempted to merge intuition and reason together\nschematically (Strack and Deutsch 2004).\nOne EDM study was identiﬁed however that shows the\nlinks between reason, intuition, and emotion. Dedeke\n(2015) does so by proposing a ‘cognitive-intuitionist’\nmodel of moral decision making. In the model, intuitions\nare referred to as reﬂexive ‘automatic cognitions,’ which\nmay or may not interact with ‘automatic emotions.’ This\ninteraction is considered part of the ‘pre-processing’ pro-\ncess which often takes place and is then ‘‘ …subject to\nreview and update by the moral reﬂection/reasoning pro-\ncess’’ (Dedeke2015, p. 446). Emotion can also ‘sabotage’\nthe moral reﬂection stage for some people and thus an\n‘emotional control variable’ is proposed ‘‘…that enables an\nindividual to …modify…their feelings stages’’ (Dedeke\n2015, p. 448). Dedeke’s ‘cognitive-intuitionist’ model\nrecognizes and captures the importance of moving future\nEDM theory in a more integrative manner, in other words,\none that incorporates reason, intuition, and emotion into the\nEDM process.\nWhile the actual degree of inﬂuence of reason versus\nintuition/emotion and the sequencing or nature of the\ninteraction remain open for debate and further research\n(Dane and Pratt 2007), virtually everyone now agrees that\nboth approaches play a role in EDM.\n38 The relationships\nbetween emotion and intuition upon each other, as well as\non moral judgment and intention, should therefore be\nindicated in any revised EDM model. As indicated by\nHaidt ( 2001, p. 828):\nThe debate between rationalism and intuitionism is an\nold one, but the divide between the two approaches\nmay not be unbridgeable. Both sides agree that people\nhave emotions and intuitions, engage in reasoning,\nand are inﬂuenced by each other. The challenge, then,\nis to specify how these processes ﬁt together.\nRationalist models do this by focusing on reasoning\nand then discussing the other processes in terms of\ntheir effects on reasoning. Emotions matter because\nthey can be inputs to reasoning …The social intu-\nitionist model proposes a very different arrangement,\n37 Ethical intention is sometimes linked with ethical behavior as\nbeing part of the ‘same phenomenon’ (Reynolds 2006a, p. 741) or\nthey can be combined together as representing one’s ‘ethical choice’\n(Kish-Gephart et al. 2010, p. 2). It may be therefore that ‘intention’\nshould be eliminated from Rest’s ( 1986) four-stage model, but might\ncontinue to act as a proxy for measuring judgment or behavior in\nEDM empirical research (see Mencl and May 2009, p. 205). For the\npurposes of the I-EDM model, intention remains theoretically distinct\nfrom behavior.\n38 Some have argued that the debate over reason versus intuition/\nemotion is actually based on whether one is experiencing a moral\ndilemma requiring a reasoning process, versus an affective or\nemotion-laden process based on reacting to a shocking situation such\nas considering the prospect of eating one’s own dog (Monin et al.,\n2007, p. 99).\nEthical Decision-Making Theory: An Integrated Approach 767\n123\n\none that fully integrates reasoning, emotion, intuition,\nand social inﬂuence.\nYet despite the claim of ‘fully’ integrating reason,\nemotion, and intuition, Haidt ( 2001) clearly makes reason\nplay a secondary role to intuition in a potential two-stage\nprocess, highlighting its lack of importance to EDM (see:\nSaltzstein and Kasachkoff 2004). As opposed to the EDM\nprocess models discussed above, the following will brieﬂy\nexplain how the I-EDM model incorporates emotion,\nintuition, reason, and rationalization along with their\npotential inter-relationships as part of a neuro-cognitive-\naffective process as depicted in Fig. 1 above.\nEmotion\nEmotion is considered an important part of the moral\njudgment and intention stages in the I-EDM model. In\nmany cases, emotion might be the ﬁrst response when\nfaced with an ethical situation or dilemma (Haidt et al.\n1993). Emotions such as empathy can lead to intuitive\njudgments (e.g., ‘affect-laden intuitions’), often referred to\nas ‘gut feelings’ about the rightness or wrongness of certain\nactions (Tofﬂer 1986). For example, the discovery that a\nwork colleague is downloading child pornography, or that\none’s ﬁrm is selling defective and dangerous goods to\nunknowing consumers, may trigger an emotional response\nsuch as a feeling of anger or disgust. This may then lead to\nan intuitive moral judgment that such behavior is unac-\nceptable and needs to be addressed. In addition to affecting\nintuitions, emotion may impact or affect the moral rea-\nsoning process (Damasio 1994; Metcalfe and Mischel\n1999; Dedeke 2015). Emotions can also lead to moral\nrationalization, for example, envy of one’s work colleagues\nwho are paid more than oneself for the same performance\nmay lead one to morally rationalize padding expense\naccounts. Emotions may impact other stages of the EDM\nprocess in addition to judgment such as intention by cre-\nating a motivation to act (see Eisenberg 2000; Huebner\net al. 2009).\nIntuition\nThe I-EDM model presumes that for most dilemmas,\nincluding those that are non-complex or involve moral\ntemptations (right versus wrong), an intuitive cognitive\nprocess takes place at least initially after being evoked by\nthe situation (Haidt 2001; Reynolds 2006a; Dedeke 2015),\nand in this respect, intuition plays a signiﬁcant role in the\nEDM process. Intuition is the more automatic and less\ndeliberative process often leading to an initial intuitive\njudgment that may or may not be acted upon. For example,\nseveral situations may provide an automatic gut ‘sense’ of\nrightness and wrongness, such as paying a bribe or over-\ncharging a customer. The moral reasoning or the moral\nrationalization process is then expected typically to follow\none’s initial intuitive judgment.\nReason\nThe I-EDM model considers the moral reasoning process\nto be just as important as intuition (Saltzstein and\nKasachkoff 2004), and not limited to merely post hoc\nrationalization (e.g., Haidt 2001). For example, in deciding\nwhether to dismiss an underperforming colleague who is\nalso considered a close friend, a more deliberative moral\nreasoning process may take place, leading to a particular\nmoral judgment. Moral reasoning provides the means by\nwhich the decision maker can reﬂect upon and resolve if\nnecessary any conﬂict among the moral standards (e.g.,\nconsequences versus duties versus fairness) or competing\nstakeholder claims. More complex ethical dilemmas would\npresumably lead to a more challenging moral reasoning\nprocess, the proper resolution of which may require a\nstronger individual moral capacity. Moral intention is then\nexpected to follow one’s moral judgment depending on\none’s integrity capacity and situational context.\nMoral Rationalization\nThis is the point during the I-EDM process when moral\nrationalization, which has not been made explicit in any of\nthe dominant EDM models, becomes important. Moral\nrationalization has over time become recognized as a more\nimportant psychological process with respect to EDM.\nMoral rationalization has been deﬁned as ‘‘ …the cognitive\nprocess that individuals use to convince themselves that\ntheir behavior does not violate their moral standards’’\n(Tsang\n2002, p. 26) and can be used to justify both small\nunethical acts as well as serious atrocities (Tsang 2002,\np. 25). Another way of thinking about rationalization is\nthrough the process of belief harmonization which involves\n‘‘…a process of arranging and revising one’s needs, beliefs,\nand personal preferences into a cohesive cognitive network\nthat mitigates against cognitive dissonance’’ (Jackson et al.\n2013, p. 238). Rest seems to suggest that the rationalization\nprocess is a type of faulty or ‘ﬂawed’ moral reasoning\n(1986, p. 18):\n…a person may distort the feelings of obligation by\ndenying the need to act, denying personal responsi-\nbility, or reappraising the situation so as to make\nalternative actions more appropriate. In other words,\nas subjects recognize the implications of [their moral\njudgment and intention] and the personal costs of\nmoral action become clear, they may defensively\n768 M. S. Schwartz\n123\n\nreappraise and alter their interpretation of the situa-\ntion [i.e., the awareness stage] so that they can feel\nhonorable, but at less cost to themselves.\nThere are several potential theories underlying moral\nrationalization. Moral rationalization may be based on the\nnotion of moral appropriation or ‘‘…the desire for moral\napproval from oneself or others’’ (Jones and Ryan 1997,\np. 664). The moral rationalization process has also been\ntied to what Ariely ( 2012, p. 53) refers to as fudge factor\ntheory, which helps explain how many are prepared to\ncheat a little bit through ‘ﬂexible’ moral reasoning while\nstill maintaining their sense of moral identity. Similarly,\nmoral balance theory permits one to engage in moral\ndeviations as long as one’s moral identity remains ‘satis-\nfactory’ (Nisan 1995).\nAnand et al. ( 2005) extend Bandura ( 1999) and Sykes\nand Matza ( 1957) by outlining the means by which one can\nrationalize corrupt or unethical acts.\n39 These methods\ninclude (Anand et al. 2005, p. 11): (i) denial of responsi-\nbility (‘My arm was being twisted’); (ii) denial of injury\n(‘No one was really harmed’); (iii) denial of victim (‘They\ndeserved it’); (iv) social weighting (‘Others are worse than\nwe are’); (v) appeal to higher authorities (‘We answered to\na higher cause’); and (vi) balancing the ledger (‘I deserve\nit’). In terms of the timing of rationalization in the EDM\nprocess, according to Anand et al. ( 2005, p. 11): ‘‘Ra-\ntionalizations can be invoked prospectively (before the act)\nto forestall guilt and resistance or retrospectively (after the\nact) to ease misgivings about one’s behavior. Once\ninvoked, the rationalizations not only facilitate future\nwrongdoing but dull awareness that the act is in fact\nwrong.’’\nIf one’s moral judgment based on moral reasoning is\ncontrary to one’s self-perceived moral identity, typically\ndue to a preference or desire to act toward fulﬁlling one’s\nself-interest, then one may engage in a biased or distorted\nprocess of moral rationalization. By doing so, one is able to\navoid experiencing the emotions of guilt, shame, or\nembarrassment. Some refer to this state as being one of\n‘moral hypocrisy’ or the appearance of being moral to\nthemselves or others while ‘‘…avoiding the cost of actually\nbeing moral’’ (Batson et al. 1999, p. 525). While moral\nrationalization is a cognitive (albeit possibly subconscious)\nprocess, it may also affect, be affected by, or work in\nconjunction with (i.e., overlap) the moral reasoning process\n(Tsang 2002), intuition (Haidt 2001), or emotion (Bandura\n1999). With few exceptions, moral rationalization is often\nunfortunately ignored or simply assumed to exist by most\nEDM models,\n40 but due to its importance is included in the\nI-EDM model.\nMoral Consultation\nOne additional potential process that can impact one’s\njudgment, intention, or behavior is that of moral consul-\ntation. Moral consultation is deﬁned as the active process\nof reviewing ethics-related documentation (e.g., codes of\nethics) or discussing to any extent one’s ethical situation\nor dilemma with others in order to receive guidance or\nfeedback. While it is clear that not all individuals will\nengage with others in helping to determine the appropri-\nate course of action, any degree of discussion with col-\nleagues, managers, family members, friends, or ethics\nofﬁcers, or the review of ethics documentation when\nfacing an ethical dilemma, would constitute moral\nconsultation.\nMoral consultation as a procedural step of EDM, while\nnot incorporated into the dominant EDM models, is referred\nto by some EDM theorists (see Sonenshein 2007; Hamilton\nand Knouse 2011). For example, Haidt ( 2001, 2007) refers\nto individuals being inﬂuenced or persuaded through their\nsocial interactions with others in his ‘social intuitionist’\nmodel and suggests that ‘‘ …most moral change happens as\na result of social interaction’’ (Haidt 2007, p. 999). Moral\nconsultation should be considered particularly important in\nan organizational setting given that ﬁrms often encourage\nand provide opportunities to their employees to discuss and\nseek ethical guidance from others or from ethics docu-\nmentation (Weaver et al. 1999; Stevens 2008). While moral\nconsultation is generally expected to improve ethical deci-\nsion making, the opposite might also occur. One may dis-\ncover through discussion that ‘unethical’ behavior is\nconsidered acceptable to others or even expected by one’s\nsuperiors potentially increasing the likelihood of acting in\nan unethical manner.\nEthical Behavior\nOne’s moral judgment ( evaluation), whether based on\nemotion ( feel), intuition ( sense), moral reasoning ( reﬂect),\nmoral rationalization ( justify), and/or moral consultation\n(conﬁrm), may then lead to moral intention ( commitment),\nwhich may then lead to ethical or unethical behavior ( ac-\ntion) (see Fig. 1 above). Each of the above processes (i.e.,\nemotion, intuition, reason, rationalization, and\n39 Heath ( 2008) provides a similar list of moral rationalizations\nwhich he refers to as ‘neutralization techniques.’\n40 Three notable exceptions include Reynolds ( 2006a), who makes\nrationalization explicit in his model as a retrospective (e.g., post hoc\nanalysis) process operating as part of the higher order conscious\nreasoning system, while the decision-making model proposed by\nTsang ( 2002) positions moral rationalization (along with situational\nfactors) as being central to the ethical decision-making process.\nDedeke ( 2015) also indicates that rationalization of one’s reﬂexive\n(intuitive or emotion-based) judgment can be part of the ‘moral\nreﬂection’ stage of EDM where moral reasoning also takes place.\nEthical Decision-Making Theory: An Integrated Approach 769\n123\n\nconsultation) can impact moral judgment either directly or\nfollowing interaction with each other. The behavior can\neither relate to ‘proscriptive’ (e.g., avoid harm) or ‘pre-\nscriptive’ (e.g., do good) actions (see Janoff-Bulman et al.\n2009) and can be of different degrees of ethicality in terms\nof the ‘rightness’ or ‘wrongness’ of the behavior (see\nHenderson 1984; Green 1994; and Kaler 2000).\nFeedback Loops\nPotential feedback loops represent the ﬁnal procedural\nstep in the I-EDM model. Behavior may be followed by\nperceived positive or negative consequences to others or\nto oneself through rewards or punishments/sanctions for\nthe decision made or actions taken. When the conse-\nquences are observed by the decision maker, learning\ninvolving internal retrospection over one’s actions can\ntake place, which may then affect one’s individual moral\ncapacity and thereby the decision-making process the next\ntime an ethical dilemma arises. According to Reynolds\n(2006a, p. 742): ‘‘ …anyone who has lain awake at night\ncontemplating the experiences of the previous day knows\nthat retrospection is a key component of the ethical\nexperience…’’ The learning might be either positive or\nnegative, for example, one might determine that acting in\nan unethical manner was worth the risks taken, or that\nacting ethically was not worth the personal costs suffered.\nIn either case, such realizations might impact future\ndecision making. Similar feedback loops including con-\nsequences and learning are included in several (but not\nall) EDM models. For example, Ferrell and Gresham\n(1985) refer to ‘evaluation of behavior,’ while Hunt and\nVitell ( 1986, p. 10) refer to ‘actual consequences’ which\nis the ‘‘major learning construct in the model’’ which\nfeeds back to one’s ‘personal experiences.’ Stead et al.\n(1990) refer to their feedback loop as one’s ‘ethical\ndecision history.’\nOne additional feedback loop of the I-EDM model (see\nFig. 1) ﬂows from behavior to awareness, in that only after\none acts (e.g., telling a white lie, fudging an account) one\nmay realize that there were ethical implications that ought\nto have been considered (i.e., if there was originally a lack\nof awareness) meaning that the matter ought to have been\nconsidered differently. The original issue or dilemma may\nthen potentially be judged again based on any of the pro-\ncesses (i.e., emotion, intuition, reason, rationalization, and/\nor consultation) leading to a different judgment and addi-\ntional behavior (e.g., admission, apology, steps to ﬁx the\nmistake, etc.). To provide greater clarity, Table 1 below\nsummarizes the various moderating factors, while Table 2\nbelow summarizes the process stages of the I-EDM model\nincluding the potential interaction between emotion, intu-\nition, reason, rationalization, and consultation.\nBasic Propositions\nIn general, according to the I-EDM model, ethical behavior\nis assumed to be more likely to take place when there is\nstrong individual moral capacity (strong moral character\ndisposition and integrity capacity), strong issue character-\nistics (high level of moral intensity and perceived impor-\ntance with a lack of complexity), strong ethical\ninfrastructure (including weak perceived opportunity with\nstrong sanctions for unethical behavior), along with weak\npersonal constraints (weak perceived need for personal\ngain, sufﬁcient time and ﬁnancial resources). Unethical\nbehavior tends to take place when there is weak individual\nmoral capacity (weak moral character disposition and\nintegrity capacity), weak issue characteristics (weak issue\nintensity and importance along with a high level of issue\ncomplexity), weak ethical infrastructure (including strong\nperceived opportunities, weak sanctions, along with strong\nauthority pressures and peer inﬂuence to engage in uneth-\nical behavior), and a lack of personal constraints (strong\nperceived need for personal gain and time pressures).\nTeaching, Research, and Managerial Implications\nThe I-EDM model has a number of important potential\nimplications for both the academic and business commu-\nnities. In terms of teaching implications, despite the history\nof major corporate scandals, a debate continues over the\nutility of business ethics education (Bosco et al. 2010). For\nthose who teach business ethics, many still argue over what\nthe proper teaching objectives should consist of (Sims and\nFelton 2006). The I-EDM model suggests that the focus of\nbusiness ethics education should be on two particular\nstages of EDM, the moral awareness stage, and the moral\njudgment stage. In terms of moral awareness, by presenting\nan array of relevant ethical dilemmas, and then sensitizing\nstudents to the potential ethical implications arising from\nthe dilemmas, might increase students’ general level of\nmoral awareness following the course.\nBy explaining the tools of moral reasoning, including\nconsequentialism and deontology, students may be better\nprepared and able to engage in moral reasoning. The\ndangers of pure egoism in the form of greed along with the\ndeﬁciencies of relativism as a moral standard need to be\npointed out. Students should also be exposed to the moral\nrationalization process, so that they will be more aware\nwhen it is taking place and can better guard against its\noccurrence. New approaches such as ‘giving voice to val-\nues’ (Gentile 2010) can also help provide a better means\nfor students and others to transition their values from\nintentions to actual behavior rather than merely focus on\nthe moral reasoning process. Ultimately, business students\n770 M. S. Schwartz\n123\n\nneed to possess the tools to be able to determine and\nactualize what might be considered ethical versus unethical\nbehavior.\nResearch that focuses on the relationship and interaction\nbetween emotion, intuition, reasoning, rationalization, and\nmoral consultation should be further pursued. It is not clear,\nfor example, the extent to which intuition and emotions\nimprove ethical decision making or hinder it. More research\non the particular aspects and types of ethical issues, beyond\nissue intensity such as issue importance and complexity,\nshould be examined to see which process (i.e., emotion,\nintuition, reason, consultation) is utilized to a greater\ndegree, and to what extent this leads to more ethical\nbehavior with fewer instances of rationalization. New sci-\nentiﬁc methods and studies of brain activity should assist in\nthis endeavor. Given that the current EDM models have\nonly partially explained the causes and processes of ethical\nbehavior, clearly more work needs to be done to revise\nEDM theory leading to more fruitful empirical examination.\nFuture EDM research should also continue to consider\nwhether certain individual and/or situational variables play\na more signiﬁcant causal or moderating role depending on\nwhich stage of EDM is taking place. For example, it may\nbe that during the awareness and judgment stages, one’s\nmoral character disposition, issue intensity, issue impor-\ntance, and issue complexity are more important, while\nduring the intention to behavior stage, integrity capacity\nand perceived ‘need for gain’ might play more important\nroles. The role of biases and heuristics should also continue\nto be examined in relation to EDM during each of the\nstages.\nIn terms of managerial implications, the I-EDM model\nsuggests that ethical infrastructure and moral consultation\neach play an important role in EDM, with formal elements\nsuch as codes and training potentially being more impor-\ntant for awareness and judgment. The model also suggests\nthat hiring practices based on seeking individuals with\nstrong moral capacities should continue to be pursued,\nespecially for managers or senior executives. For managers\nand employees, the I-EDM model may have possible\nnormative implications as well, such as avoiding the sole\nuse of intuition and emotion whenever possible, taking\nsteps to improve one’s ethical awareness potential, and to\nalways be cognizant of rationalizations and biases affecting\nthe moral reasoning process.\nLimitations\nThe proposed I-EDM model contains a number of impor-\ntant limitations. In terms of scope, the I-EDM model is\nfocused on individual decision making and behavior, rather\nthan organizational, and is designed to apply mainly to the\nbusiness context. One could argue that the model is overly\nrationalist in nature by continuing to rely on Rest ( 1986)a s\nthe dominant framework to explain the EDM process, and\nTable 1 I-EDM moderating factors\nConcept/construct Deﬁnition and relationships Key sources\nIndividual moral\ncapacity\nThe ability to avoid moral temptations, engage in the proper resolution of ethical\ndilemmas, and engage in ethical behavior. Consists of one’s moral character\ndisposition and integrity capacity. Can impact each EDM stage\nHannah et al. ( 2011)\nMoral character\ndisposition\nAn individual’s level of moral maturity based on their ethical value system, stage of\nmoral development, and sense of moral identity. Primarily impacts the moral\nawareness and moral judgment stages\nKohlberg ( 1973);\nJackson et al. ( 2013)\nIntegrity capacity The capability to consistently act in a manner consistent with one’s moral character\ndisposition. Impacts primarily the intention and behavior stages\nPetrick and Quinn ( 2000)\nEthical issue A situation requiring a freely made choice to be made among alternatives that can\npositively or negatively impact others. Can impact each EDM stage\nJones ( 1991)\nIssue intensity The degree to which consequences, social norms, proximity, or deontological/fairness\nconsiderations affect the moral imperative in a situation. Can impact each EDM stage\nButterﬁeld et al. ( 2000)\nIssue importance The perceived personal relevance of an ethical issue by an individual. Direct\nrelationship with issue intensity. Primarily impacts the moral awareness stage\nRobin et al. ( 1996)\nIssue complexity The perceived degree of difﬁculty in understanding an issue. Based on perceived\nconﬂict among moral standards or stakeholder claims or required factual information\nor assumptions needed to be made. Primarily impacts the moral awareness and moral\njudgment stages\nStreet et al. ( 2001); Warren\nand Smith-Crowe ( 2008)\nOrganization’s ethical\ninfrastructure\nThe organizational elements that contribute to an organization’s ethical effectiveness.\nCan impact each EDM stage\nTenbrunsel et al. ( 2003)\nPersonal context The individual’s current situation which can lead to ‘ethical vulnerability’ including\n‘personal need for gain’ or time/ﬁnancial constraints. Can impact each EDM stage\nAlbrecht ( 2003)\nEthical Decision-Making Theory: An Integrated Approach 771\n123\n\nthus does not represent a purely synthesized model. The\nmanner and extent to which the variables and processes\nwere depicted by the I-EDM model as portrayed in Fig. 1\ncan be criticized as being too all encompassing and thus\nlacking sufﬁcient focus. It might on the other hand be\ncriticized as failing to take into account other key variables\nor processes involved in EDM that have been suggested in\nthe literature. For example, the role of inter-personal pro-\ncesses (rather than intra-personal processes) may not be\nsufﬁciently accounted for in the I-EDM model (Moore and\nGino 2013) despite recognizing the inﬂuence of peers/ref-\nerent others, authority pressures, the rationalization process\n(‘everyone is doing it’), and the consultation process.\nFinally, each element of the I-EDM model, including the\nindividual and situational context variables as well as the\nrelationship between and overlap among the variables and\neach of the process stages of EDM, requires further\ndetailed exploration and explication which hopefully fur-\nther research will address.\nConclusion\nThis paper attempts to address several deﬁciencies that\nappear to exist in current EDM theoretical models. It does\nso by merging together the key processes, factors, and\ntheories together, including emotion, intuition, moral rea-\nsoning, moral rationalization, and moral consultation along\nwith the key individual and situational variables. The\nproposed integrated model might be considered to take a\n‘person-situation’ interactionist approach along with an\n‘intuition/sentimentalist-rationalist’ approach to moral\njudgment. It attempts to clarify the key factors inﬂuencing\nEDM, and introduces or makes more explicit other factors\nsuch as ‘moral capacity’ including ‘moral character dis-\nposition’ and ‘integrity capacity,’ and additional situational\ncharacteristics of the issue beyond merely intensity\nincluding ‘issue importance’ and ‘issue complexity.’ As\nresearch suggests: ‘‘…most all of us may commit unethical\nbehaviors, given the right circumstances’’ (De Cremer et al.\nTable 2 I-EDM process stages and constructs\nProcess stages Deﬁnition and relationship with other I-EDM constructs and stages\nMoral awareness The point in time when an individual realizes that they are faced with a situation requiring a decision or action that could\naffect the interests, welfare, or expectations of oneself or others in a manner that may conﬂict with one or more moral\nstandards (Butterﬁeld et al. 2000)\nLack of moral\nawareness\nThe state of not realizing that a dilemma has moral implications. Leads to unintentional ethical or unethical behavior\n(Tenbrunsel and Smith-Crowe 2008)\nMoral judgment Determination of the ethically appropriate course of action among alternatives. Activates the moral intention stage (Rest\n1986)\nEmotion One’s feeling state. Can impact judgment directly (Greene et al. 2001). Can also impact the moral reasoning process\n(Damasio 1994; Greene et al. 2001; Huebner et al. 2009); trigger intuitions (Haidt 2001), or can lead to rationalization\n(e.g., through feelings of guilt or sympathy for others) (Tsang 2002)\nIntuition A cognitive process involving an automatic and reﬂexive reaction leading to an initial moral judgment. Can lead to moral\njudgment directly (Haidt 2001). Can also impact emotion (Dedeke 2015), moral reasoning when there are unclear or\nconﬂicting intuitions (Haidt 2001), or lead to a rationalization process if judgment is contrary to one’s moral identity\n(Reynolds 2006a; Sonenshein 2007)\nReason The conscious and deliberate application of moral standards to a situation. Can impact moral judgment directly\n(Kohlberg 1973). Reason (‘cool system’) can also control emotions (‘hot system’) (Metcalfe and Mischel 1999).\nReason through ‘private reﬂection’ can lead to a new intuition (Haidt 2001), or can be ‘recruited’ to provide post hoc\nrationalizations (Dedeke 2015)\nMoral rationalization The conscious or unconscious process of explaining or justifying one’s intended or actual behavior in an ethically\nacceptable manner to oneself or others. Can lead to moral judgment directly (Tsang 2002). Can also impact emotion by\nforestalling or reducing guilt (Anand et al. 2005; Bandura 1999; Ariely 2012), lead to new intuitions (Haidt 2001), or\nover-ride moral reasoning through a biased or distorted cognitive process (Tsang 2002)\nMoral consultation Discussing to any extent one’s ethical dilemma with others or the review of ethical documentation (e.g., codes). Can be\noverridden by rationalization. Takes place after initial awareness, but could also take place after behavior.\nMoral intention The commitment or motivation to act according to one’s moral values. Affects moral behavior and can lead to moral\nconsultation (Rest 1986)\nEthical behavior Ethical behavior supported by one or more moral standards. Can be intentional (moral awareness) or unintentional (lack\nof moral awareness). Typically follows moral judgment and/or moral intention (Rest 1986)\nLearning The process of understanding and internalizing the impacts of one’s decisions. Can impact one’s moral capacity for\nfuture decisions (Reynolds 2006a)\n772 M. S. Schwartz\n123\n\n2010, p. 2). The possibility of a lack of moral awareness is\nalso depicted in the model, as well as ‘moral consultation’\nand the key feedback loops (i.e., learning and reassessment\nof behavior). Obviously, the proposed I-EDM model\nremains subject to further criticism, leading to the need to\nbe further modiﬁed as new EDM research is generated.\nThere are several other potential important deﬁciencies\nin the current state of EDM theory which are beyond the\nscope of this study that should be addressed as well. But if\na new proposed theoretical EDM model can at least\nproperly take into account the primary concerns raised\nabove, a potentially more robust model will have been\ndeveloped for use by a broader range of empirical\nresearchers. Given the extent of theoretical and empirical\nresearch that has now taken place, EDM in organizations\nmight be considered to be moving toward developing into a\n‘stand-alone’ academic ﬁeld (Tenbrunsel and Smith-Crowe\n2008, p. 545). Whether this eventually takes place is pri-\nmarily dependent on the strength of the theoretical EDM\nmodels being developed and tested by empirical EDM\nresearchers.\nReferences\nAgle, B. R., Hart, D. W., Thompson, J. A., & Hendricks, H. M. (Eds.).\n(2014). Research companion to ethical behavior in organiza-\ntions: Constructs and measures . Cheltenham, UK: Edward\nElgar.\nAgnihotri, J., Rapp, A., Kothandaraman, P., & Singh, R. K. (2012).\nAn emotion-based model of salesperson ethical behaviors.\nJournal of Business Ethics, 109 (2), 243–257.\nAlbrecht, W. S. (2003). Fraud examination . Thomson: Mason, OH.\nAnand, V., Ashforth, B. E., & Joshi, M. (2005). Business as usual:\nThe acceptance and perpetuation of corruption in organizations.\nAcademy of Management Executive, 19 (4), 9–23.\nAriely, D. (2012). The (honest) truth about dishonesty . New York:\nHarperCollins.\nAssociation of Certiﬁed Fraud Examiners. 2014. Report to the nations\non occupational fraud and abuse: 2014 Global Fraud Study ,\nAustin, Texas. http://www.acfe.com/rttn/docs/2014-report-to-\nnations.pdf.\nBandura, A. (1999). Moral disengagement in the perpetration of\ninhumanities. Personality and Social Psychology Review, 3 (3),\n193–209.\nBartlett, D. (2003). Management and business ethics: A critique and\nintegration of ethical decision-making models. British Journal of\nManagement, 14 , 223–235.\nBatson, D., Thompson, E. R., Seuferling, G., Whitney, H., &\nStrongman, J. A. (1999). Moral hypocrisy: appearing moral to\noneself without being so. Journal of Personality and Social\nPsychology, 77 (3), 525–537.\nBird, F. B., & Waters, G. A. (1989). The moral muteness of managers.\nCalifornia Management Review, 32 , 73–78.\nBommer, M., Gratto, C., Gravender, J., & Tuttle, M. (1987). A\nbehavioral model of ethical and unethical decision making.\nJournal of Business Ethics, 6 , 265–280.\nBosco, S. M., Melchar, D. E., Beauvais, L. L., & Desplaces, D. E.\n(2010). Teaching business ethics: The effectiveness of common\npedagogical practices in developing students’ moral judgment\ncompetence. Ethics and Education, 5 (3), 263–280.\nBrady, F. N., & Hatch, M. J. (1992). General causal models in\nbusiness ethics: An essay on colliding research traditions.\nJournal of Business Ethics, 11 , 307–315.\nBrady, F. N., & Wheeler, G. E. (1996). An empirical study of ethical\npredispositions. Journal of Business Ethics, 15 , 927–940.\nBrass, D. J., Butterﬁeld, K. D., & Skaggs, B. C. (1998). Relationships\nand unethical behavior: A social network perspective. Academy\nof Management Review, 23 (1), 14–31.\nBrown, E. (2013). Vulnerability and the basis of business ethics:\nFrom ﬁduciary duties to professionalism. Journal of Business\nEthics, 113 (3), 489–504.\nButterﬁeld, K. D., Trevin ˜o, L. K., & Weaver, G. R. (2000). Moral\nawareness in business organizations: Inﬂuences of issue-related\nand social context factors. Human Relations, 53 (7), 981–1018.\nCarroll, A. B. (1987). In search of the moral manager. Business\nHorizons, 30 (2), 7–15.\nCasali, G. L. (2011). Developing a multidimensional scale for ethical\ndecision making. Journal of Business Ethics, 104 , 485–497.\nChugh, D., Bazerman, M. H., & Banaji, M. R. (2005). Bounded\nethicality as a psychological barrier to recognizing conﬂicts of\ninterest. In D. Moore, G. Loewenstein, D. Cain, & M.\nH. Bazerman (Eds.), Conﬂicts of interest (pp. 74–95). New\nYork: Cambridge University Press.\nCraft, J. L. (2013). A review of the empirical ethical decision-making\nliterature: 2004–2011. Journal of Business Ethics, 117 , 221–259.\nDamasio, A. (1994). Descartes’ error: Emotion, reason, and the\nhuman brain . New York: Putnam.\nDamon, W., & Hart, D. (1992). Self-understanding and its role in\nsocial and moral development. In M. Bornstein & M. E. Lamb\n(Eds.), Developmental psychology: An advanced textbook (3rd\ned., pp. 421–464). Hillsdale, NJ: Erlbaum.\nDane, E., & Pratt, M. G. (2007). Exploring intuition and its role in\nmanagerial decision making. Academy of Management Review,\n32(1), 33–54.\nDe Cremer, D., Mayer, D. M., & Schminke, M. (2010). Guest editors’\nintroduction on understanding ethical behavior and decision\nmaking: A behavioral ethics approach. Business Ethics Quar-\nterly, 20 (1), 1–6.\nDe George, R. T. (2010). Business ethics (7th ed.). New York:\nPrentice Hall.\nDedeke, A. (2015). A cognitive-intuitionist model of moral judgment.\nJournal of Business Ethics, 126 , 437–457.\nDonaldson, T., & Dunfee, T. W. (1999). Ties that bind: A social\ncontracts approach to business ethics . Cambridge, MA: Harvard\nBusiness School Press.\nDrumwright, M. E., & Murphy, P. E. (2004). How advertising\npractitioners view ethics: Moral muteness, moral myopia, and\nmoral imagination. Journal of Advertising, 33 (2), 7–24.\nDubinsky, A. J., & Loken, B. (1989). Analyzing ethical decision\nmaking in marketing. Journal of Business Research, 19 , 83–107.\nEisenberg, N. (2000). Emotion, regulation, and moral development.\nAnnual Review of Psychology, 51 , 665–697.\nElfenbein, H. A. (2007). Emotion in organizations. The Academy of\nManagement Annals, 1 (1), 315–386.\nElm, D. R., & Radin, T. J. (2012). Ethical decision making: Special or\nno different? Journal of Business Ethics, 107 (3), 313–329.\nEthics Resource Center (2014). 2013 National business ethics survey.\nArlington, VA.\nFerrell, O. C., & Gresham, L. G. (1985). A contingency framework\nfor understanding ethical decision making in marketing. Journal\nof Marketing, 49 (3), 87–96.\nFerrell, O. C., Gresham, L. G., & Fraedrich, J. (1989). A synthesis of\nethical decision models for marketing. Journal of Macromar-\nketing, 9 (2), 55–64.\nEthical Decision-Making Theory: An Integrated Approach 773\n123\n\nFishbein, M., & Ajzen, I. (1975). Belief, attitude, intention, and\nbehavior: An introduction to theory and research . Reading, MA:\nAddison-Wesley.\nFord, R. C., & Richardson, W. D. (1994). Ethical decision making: A\nreview of the empirical literature. Journal of Business Ethics, 13 ,\n205–221.\nGaudine, A., & Thorne, L. (2001). Emotion and ethical decision-making\nin organizations. Journal of Business Ethics, 31 (2), 175–187.\nGentile, M. C. (2010). Giving voice to values: How to speak your\nmind when you know what’s right . New Haven, CT: Yale\nUniversity Press.\nGioia, D. (1992). Pinto ﬁres and personal ethics: A script analysis of\nmissed opportunities.Journal of Business Ethics, 11(5/6), 379–389.\nGreen, R. M. (1994). The ethical manager . New York: Macmillan\nCollege Publishing.\nGreene, J. D., Sommerville, R. B., Nystrom, L. E., Darley, J. M., &\nCohen, J. (2001). An fMRI investigation of emotional engage-\nment in moral judgement. Science, 293 , 2105–2108.\nHaidt, J. (2001). The emotional dog and its rational tail: A social\nintuitionist approach to moral judgment. Psychological Review,\n4, 814–834.\nHaidt, J. (2007). The new synthesis in moral psychology. Science,\n316, 998–1002.\nHaidt, J., Koller, S., & Dias, M. (1993). Affect, culture, and morality,\nor is it wrong to eat your dog? Journal of Personality and Social\nPsychology, 65 , 613–628.\nHaines, R., Street, M. D., & Haines, D. (2008). The inﬂuence of\nperceived importance of an ethical issue on moral judgment,\nmoral obligation, and moral intent. Journal of Business Ethics,\n81, 387–399.\nHamilton, J. B., & Knouse, S. B. (2011). The experience-focused model\nof ethical action. In S. W. Gilliland, D. D. Steiner, & D. P. Skarlicki\n(Eds.), Emerging perspectives on organizational justice and ethics\n(pp. 223–257). Charlotte, NC: Information Age Publishing.\nHannah, S. T., Avolio, B. J., & May, D. R. (2011). Moral maturation\nand moral conation: A capacity approach to explaining moral\nthought and action. Academy of Management Review, 36 (4),\n663–685.\nHeath, J. (2008). Business ethics and moral motivation: A crimino-\nlogical perspective. Journal of Business Ethics, 83 , 595–614.\nHenderson, V. E. (1984). The spectrum of ethicality. Journal of\nBusiness Ethics, 3 (2), 163–171.\nHerndon, N. C, Jr. (1996). A new context for ethics education\nobjectives in a college of business: Ethical decision-making\nmodels. Journal of Business Ethics, 15 (5), 501–510.\nHuebner, B., Dwyer, S., & Hauser, M. (2009). The role of emotion in\nmoral psychology. Trends in Cognitive Sciences, 13 (1), 1–6.\nHunt, S. D., & Vitell, S. (1986). A general theory of marketing ethics.\nJournal of Macromarketing, 6 (1), 5–16.\nJackson, R. W., Wood, C. M., & Zboja, J. J. (2013). The dissolution\nof ethical decision-making in organizations: A comprehensive\nreview and model. Journal of Business Ethics, 116 , 233–250.\nJanoff-Bulman, R., Sheikh, S., & Hepp, S. (2009). Proscriptive versus\nprescriptive morality: Two faces of moral regulation. Journal of\nPersonality and Social Psychology, 96 (3), 521–537.\nJones, T. M. (1991). Ethical decision making by individuals in\norganizations: An issue contingent model. The Academy of\nManagement Review, 16 (2), 366–395.\nJones, T. M., & Ryan, L. V. (1997). The link between ethical\njudgment and action in organizations: A moral approbation\napproach. Organization Science, 8 (6), 663–680.\nKahneman, D. (2003). A perspective on judgment and choice.\nAmerican Psychologist, 58\n, 697–720.\nKaler, J. (2000). Reasons to be ethical: Self-interest and ethical\nbusiness. Journal of Business Ethics, 27 (1/2), 161–173.\nKidder, R. M. (1995). How good people make tough choices:\nResolving the dilemmas of ethical living . New York: Simon &\nSchuster.\nKish-Gephart, J. J., Harrison, D. A., & Trevin ˜o, L. K. (2010). Bad\napples, bad cases, and bad barrels: Meta-analytic evidence about\nsources of unethical decisions at work. Journal of Applied\nPsychology, 95 (1), 1–31.\nKohlberg, L. (1973). The claim to moral adequacy of a highest stage\nof moral judgment. The Journal of Philosophy, 70 (18), 630–646.\nLapsley, D. K., & Narvaez, D. (2004). Moral development, self, and\nidentity. Mahwah, NJ: Lawrence Erlbaum Associates.\nLehnert, K., Park, Y., & Singh, N. (2015). Research note and review\nof the empirical ethical decision-making literature: Boundary\nconditions and extensions. Journal of Business Ethics , 129,\n195–219.\nLiedka, J. M. (1989). Value congruence: The interplay of individual\nand organizational value systems. Journal of Business Ethics,\n8(10), 805–815.\nLoe, T. W., Ferrell, L., & Mansﬁeld, P. (2000). A review of empirical\nstudies assessing ethical decision making in business. Journal of\nBusiness Ethics, 25 (3), 185–204.\nMarquardt, N., & Hoeger, R. (2009). The effect of implicit moral\nattitudes on managerial decision-making: An implicit social\ncognition approach. Journal of Business Ethics, 85 , 157–171.\nMay, D. R., & Pauli, K. P. (2002). The role of moral intensity in\nethical decision making. Business and Society, 41 (1), 84–117.\nMcFerran, B., Aquino, K., & Duffy, M. (2010). How personality and\nmoral identity relate to individuals’ ethical ideology. Business\nEthics Quarterly, 20 (1), 35–56.\nMcMahon, J. M. and Harvey, R. J. (2007). The effect of moral\nintensity on ethical judgment. Journal of Business Ethics , 72,\n335–357.\nMencl, J., & May, D. R. (2009). The effects of proximity and empathy\non ethical decision-making: An exploratory investigation. Jour-\nnal of Business Ethics, 85 , 201–226.\nMessick, D. M., & Bazerman, M. H. (1996). Ethical leadership and\nthe psychology of decision making. Sloan Management Review,\n37(2), 9–22.\nMetcalfe, J., & Mischel, W. (1999). A hot/cool system analysis of\ndelay of gratiﬁcation: Dynamics of willpower. Psychological\nReview, 106 , 3–19.\nMonin, B., Pizarro, D. A., & Beer, J. S. (2007). Deciding versus\nreacting: Conceptions of moral judgment and the reason-affect\ndebate. Review of General Psychology, 11 (2), 99–111.\nMoore, G., & Gino, F. (2013). Ethically adrift: How others pull our\nmoral compass from true North, and how we can ﬁx it. Research\nin Organizational Behavior, 33 , 53–77.\nMudrack, P. E., & Mason, E. S. (2013). Dilemmas, conspiracies, and\nSophie’s choice: Vignette themes and ethical judgments. Journal\nof Business Ethics, 118 , 639–653.\nMuraven, M., Baumeister, R. F., & Tice, D. M. (1999). Longitudinal\nimprovement of self-regulation through practice: Building self-\ncontrol strength through repeated exercise. Journal of Social\nPsychology, 139 , 446–457.\nNisan, M. (1995). Moral balance model. In W. M. Kurtines & J.\nL. Gewirtz (Eds.), Moral development: An introduction (pp.\n475–492). Boston: Allyn & Bacon.\nO’Fallon, M. J., & Butterﬁeld, K. D. (2005). A review of the\nempirical ethical decision-making literature: 1996–2003. Jour-\nnal of Business Ethics, 59 , 375–413.\nPalazzo, G., Krings, F., & Hoffrage, U. (2012). Ethical blindness.\nJournal of Business Ethics, 109 , 323–338.\nPan, Y., & Sparks, J. R. (2012). Predictors, consequence, and\nmeasurement of ethical judgments: Review and meta analysis.\nJournal of Business Research, 65 , 84–91.\n774 M. S. Schwartz\n123\n\nPetrick, J. A., & Quinn, J. F. (2000). The integrity capacity construct\nand moral progress in business. Journal of Business Ethics, 23 ,\n3–18.\nPimental, J. R. C., Kuntz, J. R., & Elenkov, D. S. (2010). Ethical\ndecision-making: An integrative model for business practice.\nEuropean Business Review, 22 (4), 359–376.\nPrinz, J. J., & Nichols, S. (2010). Moral emotions. In J. M. Doris, &\nThe Moral Psychology Research Group (Eds.), The moral\npsychology handbook (pp. 111–146). Oxford: Oxford University\nPress.\nRandall, D. M. (1989). Taking stock: Can the theory of reasoned\naction explain unethical conduct? Journal of Business Ethics,\n8(11), 873–882.\nRandall, D. M., & Gibson, A. M. (1990). Methodology in business\nethics research: A review and critical assessment. Journal of\nBusiness Ethics, 9 , 457–471.\nRest, J. R. (1984). The major components of morality. In W.\nM. Kurtines & J. L. Gewirtz (Eds.), Morality, moral behavior,\nand moral development (pp. 24–38). New York: Wiley.\nRest, J. R. (1986). Moral development: Advances in research and\ntheory. New York: Praeger.\nRest, J., Narvaez, D., Bebeau, M. J., & Shoma, S. J. (1999).\nPostconventional thinking: A new-Kohlbergian approach . Mah-\nwah, New Jersey: Lawrence Erlbaum Associates.\nReynolds, S. J. (2006a). A neurocognitive model of the ethical\ndecision-making process: Implications for study and practice.\nJournal of Applied Psychology, 91 (4), 737–748.\nReynolds, S. J. (2006b). Moral awareness and ethical predispositions:\nInvestigating the role of individual differences in the recognition\nof moral issues. Journal of Applied Psychology, 91 (1), 233–243.\nReynolds, S. J. (2008). Moral attentiveness: Who pays attention to the\nmoral aspects of life? Journal of Applied Psychology, 93 (5),\n1027–1041.\nRobin, D. P., Reidenbach, R. E., & Forrest, P. J. (1996). The\nperceived importance of an ethical issue as an inﬂuence on the\nethical decision-making of ad managers. Journal of Business\nResearch, 35 , 17–28.\nRossouw, D., & Stu ¨ ckelberger, C. (Eds.) (2012). Global survey of\nbusiness ethics: In training, teaching and research . http://www.\nglobethics.net/documents/4289936/13403236/GlobalSeries_5_\nGlobalSurveyBusinessEthics_text.pdf.\nRuedy, N. E., Moore, C., Gino, F., & Schweitzer, M. E. (2013). The\ncheater’s high: The unexpected affective beneﬁts of unethical\nbehavior. Journal of Personality and Social Psychology, 105 (4),\n531–548.\nRuedy, N. E., & Schweitzer, M. E. (2010). In the moment: The effect\nof mindfulness on ethical decision making. Journal of Business\nEthics, 95 , 73–87.\nSaltzstein, H. D., & Kasachkoff, T. (2004). Haidt’s moral intuitionist\ntheory: A psychological and philosophical critique. Review of\nGeneral Psychology, 8 (4), 273–282.\nSalvador, R., & Folger, R. G. (2009). Business ethics and the brain.\nBusiness Ethics Quarterly, 19 (1), 1–31.\nSchlenker, B. R. (2008). Integrity and character: Implications of\nprincipled and expedient ethical ideologies. Journal of Social\nand Clinical Psychology, 27 (10), 1078–1125.\nSchminke, M. (1998). Managerial ethics: Moral management of\npeople and processes . Mahwah, NJ: Lawrence Erlbaum and\nAssociates.\nSchwartz, M. S. (2005). Universal moral values for corporate codes of\nethics. Journal of Business Ethics, 59 (1), 27–44.\nSchwartz, M. S., & Carroll, A. (2003). Corporate social responsibil-\nity: A three domain approach. Business Ethics Quarterly, 13\n(4),\n503–530.\nSinger, M. S. (1996). The role of moral intensity and fairness\nperception in judgments of ethicality: A comparison of\nmanagerial professionals and the general public. Journal of\nBusiness Ethics , 15, 469–474.\nSims, R. R., & Felton, E. L. (2006). Designing and delivering\nbusiness ethics teaching and learning. Journal of Business\nEthics, 63 , 297–312.\nSonenshein, S. (2007). The role of construction, intuition, and\njustiﬁcation in responding to ethical issues at work: The\nsensemaking-intuition model. Academy of Management Review,\n32(4), 1022–1040.\nStead, W. E., Worrell, D. L., & Stead, J. G. (1990). An integrative model\nfor understanding and managing ethical behavior in business\norganizations. Journal of Business Ethics, 9 (3), 233–242.\nStevens, Betsy. (2008). Corporate ethical codes: Effective instruments\nfor inﬂuencing behavior. Journal of Business Ethics, 78 (4),\n601–609.\nStrack, F., & Deutsch, R. (2004). Reﬂective and impulsive determi-\nnants of social behavior. Personality and Social Psychological\nReview, 8 , 220–247.\nStreet, M. D., Douglas, S. C., Geiger, S. W., & Martinko, M. J.\n(2001). The impact of cognitive expenditure on the ethical\ndecision-making process: The cognitive elaboration model.\nOrganizational Behavior and Human Decision Processes,\n86(2), 256–277.\nSykes, G., & Matza, D. (1957). Techniques of neutralization: A\ntheory of delinquency. American Sociological Review, 22 ,\n664–670.\nTangney, J. P., Stuewig, J., & Mashek, D. J. (2007). Moral emotions\nand moral behavior. Annual Review of Psychology, 58 , 345–372.\nTenbrunsel, A. E., & Messick, D. M. (2004). Ethical fading: The role\nof self-deception in unethical behavior. Social Justice Research,\n17(2), 223–236.\nTenbrunsel, A. E., & Smith-Crowe, K. (2008). Ethical decision\nmaking: Where we’ve been and where we’re going. Academy of\nManagement Annals, 2 (1), 545–607.\nTenbrunsel, A. E., Smith-Crowe, K., & Umphress, E. (2003).\nBuilding houses on rocks: The role of the ethical infrastructure\nin organizations. Social Justice Research, 16 (3), 285–307.\nTofﬂer, B. (1986). Tough choices: Managers talk ethics . New York:\nWiley.\nTorres, M. B. (2001). Character and decision making . Unpublished\nDissertation, University of Navarra.\nTrevin˜o, L. K. (1986). Ethical decision making in organizations: A\nperson-situation interactionist model. Academy of Management\nReview, 11 (3), 601–617.\nTrevin˜o, L. K., Butterﬁeld, K. D., & McCabe, D. L. (1998). The\nethical context in organizations: Inﬂuences on employee atti-\ntudes and behaviors. Business Ethics Quarterly, 8 , 447–476.\nTrevin˜o, L. K., Weaver, G. R., & Reynolds, S. J. (2006). Behavioral\nethics in organizations. Journal of Management, 32 (6), 951–990.\nTsang, J. A. (2002). Moral rationalization and the integration of\nsituational factors and psychological processes in immoral\nbehavior. Review of General Psychology, 6 (1), 25–50.\nU.S. Sentencing Commission (2014). Organizations receiving ﬁnes or\nrestitution. Sourcebook for Federal Sentencing Statistics. www.\nussc.gov/research-and-publications/annual-reports-sourcebooks/\n2014/sourcebook-2014.\nValentine, S., & Hollingworth, D. (2012). Moral intensity, issue\nimportance, and ethical reasoning in operations situations.\nJournal of Business Ethics, 108 , 509–523.\nValentine, S., Nam, S. H., Hollingworth, D., & Hall, C. (2013).\nEthical context and ethical decision making: Examination of an\nalternative statistical approach for identifying variable relation-\nships. Journal of Business Ethics, 68 , 1–18.\nVictor, B., & Cullen, J. B. (1988). The organizational bases of ethical\nwork climates. Administrative Science Quarterly, 33 (1),\n101–125.\nEthical Decision-Making Theory: An Integrated Approach 775\n123\n\nWarren, D. E., & Smith-Crowe, K. (2008). Deciding what’s right: The\nrole of external sanctions and embarrassment in shaping moral\njudgments in the workplace. Research in Organizational\nBehavior, 28 , 81–105.\nWatson, G. W., Berkley, R. A., & Papamarcos, S. D. (2009).\nAmbiguous allure: The value-pragmatics model of ethical\ndecision making. Business and Society Review, 114 (1), 1–29.\nWeaver, G. R., Trevin ˜o, L. K., & Cochran, P. L. (1999). Corporate\nethics practices in the mid-1990’s: An empirical study of the\nFortune 1000. Journal of Business Ethics, 18 (3), 283–294.\nWeber, J. (1993). Exploring the relationship between personal values\nand moral reasoning. Human Relations, 46 (4), 435–463.\nWeber, J. (1996). Inﬂuences upon managerial moral decision-making:\nNature of the harm and magnitude of consequences. Human\nRelations, 49 (1), 1–22.\nWebley, S. (2011). Corporate ethics policies and programmes: UK\nand Continental Europe survey 2010 . London: UK, Institute of\nBusiness Ethics.\nWerhane, P. H. (1998). Moral imagination and the search for ethical\ndecision-making in management. Business Ethics Quarterly,\nRufﬁn Series, 1 , 75–98.\nWhittier, N. C., Williams, S., & Dewett, T. C. (2006). Evaluating\nethical decision-making models: A review and application.\nSociety and Business Review, 1 (3), 235–247.\nWoiceshyn, J. (2011). A model for ethical decision making in\nbusiness: reasoning, intuition, and rational moral principles.\nJournal of Business Ethics, 104 , 311–323.\nWright, J. C. (2005). The role of reasoning and intuition in moral\njudgment: A review . Unpublished PhD Comprehensive Exam,\nUniversity of Wyoming.\nYu, Y. M. (2015). Comparative analysis of Jones’ and Kelley’s\nethical decision-making models. Journal of Business Ethics , 130,\n573–583.\n776 M. S. Schwartz\n123\n\nReproduced with permission of the copyright owner. Further reproduction prohibited without\npermission.	Ethical Decision-Making Theory: An Integrated Approach\nMark S. Schwartz 1\nReceived: 15 December 2014 / Accepted: 23 September 2015 / Published online: 26 October 2015\n/C211 Springer Science+Business Media Dordrecht 2015\nAbstract Ethical decision-making (EDM) descriptive\ntheoretical models often conﬂict with each other and typ-\nically lack comprehensiveness. To address this deﬁciency,\na revised EDM model is proposed that consolidates and\nattempts to bridge together the varying and sometimes\ndirec...	en	0.9	uploaded	18515	121381	2025-08-27 20:36:49.365258	2025-08-27 20:36:49.36526	\N	1	\N	\N
60	Rothstein - 1987 - Cynthia Ozick's Rabbinical Approach to Literature	file	document	\N	pdf	Rothstein - 1987 - Cynthia Ozick's Rabbinical Approach to Literature.pdf	uploads/9d93cb652a7141988450b450776d4bc3_Rothstein_-_1987_-_Cynthia_Ozicks_Rabbinical_Approach_to_Literature.pdf	125246	\N	Reproduced with permission of the copyright owner.  Further reproduction prohibited without permission.\nCYNTHIA OZICK'S RABBINICAL APPROACH TO LITERATURE\nRothstein, Mervyn\nNew York Times; Mar 25, 1987; ProQuest One Academic\npg. C.24\n	Reproduced with permission of the copyright owner.  Further reproduction prohibited without permission.\nCYNTHIA OZICK'S RABBINICAL APPROACH TO LITERATURE\nRothstein, Mervyn\nNew York Times; Mar 25, 1987; ProQuest One Academic\npg. C.24\n	en	0.9	uploaded	31	233	2025-08-27 20:37:44.067211	2025-08-27 20:37:44.067215	\N	1	\N	\N
61	Foster - 2025 - Marx and Communal Society	file	document	\N	pdf	Foster - 2025 - Marx and Communal Society.pdf	uploads/Foster-2025-Marx-and-Communal-Society.pdf	252937	{"prov_type": "prov:Entity"}	Marx and Communal Society\nJOHN BELLAMY FOSTER\n“Ultimately communism is the only thing that is important about [Karl] \nMarx’s thought,” Hungarian British political theorist R. N. Berki observed \nin 1983.1 Although this was an exaggeration, it is undeniable that Marx’s \nbroad conception of communal society/communism formed the basis of \nhis entire critique of class society and his vision of a viable future for hu-\nmanity. Yet, there have been few attempts to engage systematically with \nthe development of this aspect of Marx’s thought as it emerged over the \ncourse of his life, due to the complexity of his approach to the question of \ncommunal production in history and the philosophical, anthropological, \nand political-economic challenges that this presented, extending to our \nown day. Still, Marx’s approach to communal society is of genuine signifi-\ncance not only in understanding his thought as a whole, but also in help-\ning guide humanity past the iron cage of capitalist society. In addition to \npresenting a philosophical anthropology of communism, he delved into \nthe history and ethnology of actual communal social formations. This led \nto concrete investigations into communal production and exchange. All \nof this played into his conception of the communism of the future as a \nsociety of associated producers.2\nIn our time, communal production and exchange, and elements of a com-\nmunal state, have been developed, with varying degrees of success, in a \nnumber of socialist societies following revolutions, notably in the Soviet \nUnion, China, Cuba, Venezuela, and elsewhere around the world. Marx’s \nunderstanding of the history, philosophy, anthropology, and political econ-\nomy of communal/collective society is thus an important source of insight \nand vision, not only with respect to the past, but also the present and future.\nThe Social Ontology of Communal Production\nMarx was a product from his earliest age of the radical Enlightenment, \ninfluenced in this respect by both his father, Heinrich Marx, and his men-\ntor and future father-in-law, Ludwig von Westphalen. To this was added \nhis deep encounter with German idealist philosophy, as exemplified by \nthe work of G. W. F. Hegel. Marx was an accomplished scholar of Greek \nJohn Bellamy Foster is editor of Monthly Review and professor emeritus of sociology \nat the University of Oregon. He is author most recently of The Dialectics of Ecology (2024) \nand Breaking the Bonds of Fate: Epicurus and Marx (forthcoming 2025)—both published by \nMonthly Review Press.\nmonthlyreviewarchives.org\nDOI: 10.14452/MR-071-08-2020-01_1\n47\n\nantiquity, engaging in intense studies of both Aristotle, whom he viewed \nas the greatest of the Greek philosophers, and Epicurus, the leading ma -\nterialist thinker of the Hellenistic world. He completed his doctoral the -\nsis on Epicurus’s philosophy of nature in 1841, emerging as a materialist \nsoon engaged with the idea of communism.3\nMarx read Pierre-Joseph Proudhon’s What Is Property? as early as 1842. \nHowever, along with other radical thinkers in Germany in the 1840s, he \nfirst took up discussions of the contemporary communistic movements \nemerging in France as a result of the spread of these ideas to Germany in \nthe Prussian official Lorenz von Stein’s The Socialism and Communism in Pres-\nent-Day France (1842) and Moses Hess’s Socialism and Communism (1843), which \ntook the form of a critical commentary on von Stein. Hess was the cofound-\ner in January 1842 of the liberal newspaper Rheinische Zeitung, which Marx \nbecame editor-in-chief of in October 1842. One of Marx’s first tasks as editor \nwas to reply to accusations that the Rheinische Zeitung was a communist pa-\nper due to the publication of two articles on housing and communist forms \nof governance, and a piece on followers of Charles Fourier—all written by \nHess. Marx’s reply on behalf of the Rheinische Zeitung was very circumspect, \nneither supporting nor opposing communism, while making it clear that \n“the Rheinische Zeitung…does not admit that communist ideas in their pres-\nent form possess even theoretical reality, and therefore can still less desire \ntheir practical realisation.” Marx mentions Fourier here for the first time, \nalong with Victor Prosper Considérant and Proudhon, also referring to the \nidea of communism in Plato’s Republic.4\nFor most thinkers at the time, the question of communism was one \nsimply of opposition to private property and was treated purely philo -\nsophically, largely from an idealist standpoint. Hess saw society as hav -\ning originated in a social compact between individuals—as distinct from \nboth the Epicurean notion of the establishment of an original social \ncontract between kinship groupings, which was defeated and then res -\nurrected in more limited, class-mediated forms, following social revolt \nand the death of kings; and Aristotle’s sense of humanity as a political/\nsocial animal.5 The individualistic view of property of early French and \nGerman socialism reflected the influence of Proudhon, who, following \nJean-Jacques Rousseau, failed to distinguish between private property and \nproperty in general, seeing property simply as “theft.” 6 Proudhon thus \nfailed to comprehend the notion of property as having its active principle \nin appropriation from nature. His analysis implicitly denied the universality \nof property in human society, and, more specifically, the existence of \ncommon property, as depicted in Hegel and Marx. Still, for Hegel, prop -\nerty, even if arising universally in appropriation from nature, existed as \n48 MONTHLY REVIEW / J ULY –A UGUST  2025\n\nan abstract right only as private property. Abstract right thus led to the \ndissolution of common property.7\nIn contrast to these dominant bourgeois views, which penetrated into \nsocialist thought, Marx’s own perspective was both historical and mate -\nrialist. Humans were from the start social animals. Production, based on \nthe appropriation from nature for human purposes, was originally com -\nmunal—and held in common. The complete dominance of private prop -\nerty as alienated appropriation/production only came into being under \ncapitalism, preceded by “thousands of centuries” of human history.8 Marx \ndrew from the outset on his extensive knowledge of ancient Greek and \nRoman philosophy and history and on traces of early Germanic history as \nrevealed by Caesar in The Gallic Wars and by Tacitus in his Germania, which \nMarx translated in 1837.9 Throughout his life, Marx continued to explore \nwhatever historical and anthropological evidence became available with \nrespect to communal production, exchange, and property, while also con-\nsidering the inner logic of communal production via philosophical and \neconomic conceptions. As a student of classical antiquity, he would most \nlikely have been aware of ancient accounts of the household communi -\nties in India with common tillage of the soil, recorded by Alexander the \nGreat’s admiral Nearchus and related by Strabo.10\nRemnants of the old Germanic Mark system of common tenure and \ncollective production on the land survived into Marx’s lifetime in the \nregion around Trier, where he grew up. His father, a lawyer, had dis -\ncussed the ramifications of these collective property rights with him in \nhis youth.11 Signs of customary right carrying over from the commons of feu-\ndal times, were evident throughout early nineteenth-century Germany. \nIn the same month in which he addressed the question of communism \nin the Rheinische Zeitung, Marx wrote his first political-economy article on \n“Debates on the Law on Thefts of Wood,” in which he strongly defend -\ned the customary rights of the Rhenish peasant that had persisted into \nthe modern era related to the removal of dead wood (together with dead \nleaves and berries) from the forests, an act that was then criminalized. \nIn this context, he explored how such customary rights were being sys -\ntematically expropriated by landowners in league with the state. “We are \nonly surprised,” he declared, “that the forest owner is not allowed to heat \nhis stove with the wood thieves.”12\nMarx’s critique of private property in the 1840s and ’50s depended on an \nontological conception of human beings that emphasized social and com-\nmunal relations arising out of the appropriation of nature. Most of the con-\ncrete knowledge of the history of antiquity in Europe prior to the mid-nine-\nteenth century was dependent on ancient Greek and Roman sources. As \nM ARX  & C OMMUNAL  S OCIETY  49\n\nEric Hobsbawm wrote in the introduction to Marx’s Pre-Capitalist Economic \nFormations (part of the latter’s Grundrisse, written in 1857–1858), “Neither a \nclassical [European] education nor the material then available made a seri-\nous knowledge of Egypt and the ancient Middle East possible.”13 This was \ntrue also of India, Ceylon, and Java to varying degrees, though there Marx \nwas able to rely on the questionable accounts of British and Dutch colonial \nadministrators. The brief treatment of communal property relations under \nthe Incas in Peru included in William Prescott’s History of the Conquest of Peru \n(1847) was to occupy an important place in Marx’s analysis in the Grundrisse \nand Capital. From the fifteenth up through the middle of the sixteenth \ncentury, the predominant tribe of the Inca social formation in present-day \nPeru, Ecuador, and Bolivia was “subdivided into 100 clan communes (ayllu), \nwhich gradually developed into village communes.”14\nPrior to the “revolution in ethnological time” giving rise to modern \nanthropological studies, beginning in 1859, the historical and anthropo -\nlogical knowledge of communal production in early kinship and tribu -\ntary-based societies available to Marx was limited.15 Marx’s historical and \nanthropological knowledge of communal production in his early years \nwas thus heavily weighted toward ancient Greek and Roman class soci -\nety, where earlier communal forms of production had left their mark. \nNevertheless, he relied on his deep ontological understanding of labor \nand production in society, allowing him to develop a penetrating analysis \nthat, at least in its broad outlines, remains relevant today.\nUnderlying Marx’s entire analysis was his materialist ontology of human \nlabor and production first introduced in his Economic and Philosophical Manu-\nscripts of 1844 and that became the basis of his materialist conception of his-\ntory as presented in 1845–1846 in the German Ideology, written with Frederick \nEngels. In Marx’s social ontology, labor and production was a social process \nin which individuals took part as social beings. Human history could be \nperceived in changing “modes of appropriation.”16 All human culture was \nrooted in the reality of human labor and the appropriation of nature, and \ntherefore in the formation of property relations within communities, which \nwere originally kinship communities. The first form of property depicted in \nThe German Ideology was tribal property, associated with hunting and gather-\ning and the earliest forms of agriculture. These were characterized by “the \noriginal unity between a particular form of community (clan) and the corre-\nsponding property in nature.” Here the division of labor remained undevel-\noped. Society was patriarchal, while the first forms of the division of labor \nwere associated with the development of the “slavery latent in the family.” \nIn this initial description of tribal society in Marx, there is not yet any direct \nmention of communal production or property.17\n50 MONTHLY REVIEW / J ULY –A UGUST  2025\n\nIt is worth noting that there is no reference in The German Ideology to \n“primitive [original] communism,” a term that neither Marx nor Engels \never used except in reference to the “Asiatic communal system,” the Slavic \nform of land tenure, and, somewhat more tenuously, the precursors of the \nGerman Mark, and did not apply to hunting and gathering societies. The \nlatter, though communal in their arrangements, were not viewed as modes \nof production in the full sense, but as clan-kinship societies. Use of the term \n“primitive communism” to describe hunting and gathering societies specif-\nically was a later importation within the Second and Third Internationals.18\nThe second historical form of property in The German Ideology  is “the \nancient communal and state property,” arising “from the union of several \ntribes into a city by agreement or by conquest, and which is still accom -\npanied by slavery.”19 Private “property in land” in antiquity, as Marx later \nexplained in his Ethnological Notebooks, arose “partly from the disentangle-\nment of the individual rights of the kindred or tribesmen from the collective rights \nof the Family or Tribe…partly from the growth and transmutation of the Sover-\neignty of the Tribal Chief .” Private property in land thus was initially medi -\nated by the communal land ownership ( ager publicus), and yet gradually \nserved to introduce class relations that weakened the collective order.20\nThe notion of the “ancient commune and state” governing social rela -\ntions in antiquity was associated with the polis as a communally governed \nsociety arising out of earlier tribal relations. As Patricia Springborg wrote \nin “Marx, Democracy, and the Ancient Polis,” the polis was “an urban \ncommune in which private property existed alongside communal prop -\nerty.” The Greek polis, in Marx’s conception, Springborg explained, held \n“in suspension tribal and communal forms while inaugurating the state \nas a phenomenon.”21 The economy and conversely the state, as Hegel and \nMarx, and, later, Karl Polanyi, argued, were not yet disembedded from \nthe polis. Hence, the alienation of the state from civil society in the mod-\nern sense did not yet exist, allowing for the persistence of communal \nforms, together with class divisions.22\nFor Marx, slavery, though in many ways constituting the material founda-\ntion of the Greek polis of the golden age, was subordinate to the communal \norder governing property relations, arising out of previous kinship relations. \nThe growth of mobile property and money, particularly coinage, commenc-\ning in Lydia in the seventh century BCE, had the effect of intensifying class \ndistinctions. This development was crucial in accounting for the origins and \nexpansion of ancient chattel slavery, while also contributing to the eventual \ndissolution of the ancient communal order of Greece and Rome.23\nIndeed, although heavily emphasizing the role of slavery in antiquity, \nMarx never characterized ancient society as an actual “slave mode of \nM ARX  & C OMMUNAL  S OCIETY  51\n\nproduction,” as was later to become common in Marxist theory. Thus, in \nPerry Anderson’s Passages from Antiquity to Feudalism , we are told that the \n“decisive innovation” of the ancient Greco-Roman world was the “mas -\nsive scale of chattel slavery” or the “slave mode of production.”24 In con-\ntrast, Marx saw slave production in antiquity as a secondary attribute \nof the communal and state form, associated with the growth of money \nand trade. At its core, the polis was rooted, from primordial times, in \ntribal or kinship relations, as in the Greek phratry, out of which its class \ndivisions between the aristocracy and the demos (in the case of Athens) \nwere to emerge with the growth of private property. Slavery was viewed \nby Marx as something of an add-on. Still, this did not keep him from \nnoting in the Grundrisse, with the golden ages of Pericles’s Athens and \nAugustus’s Rome clearly in mind, that economically “direct forced la -\nbour is the foundation of the ancient world; the community rests on \nthis as its foundation.”25\nThe persistent critiques of unlimited acquisition of wealth that played \nsuch a prominent role in Greek philosophy from Aristotle to Epicurus \nwere characterized by Marx (and by classical scholars up our day) as re -\nsulting from changes in the society that could be traced primarily to the \nfirst signs of a money economy, mainly in the interstices and in trading \nnations, opening the way to the systematic pursuit of wealth for its own \nsake, and destabilizing prior social relations. 26 As Marx wrote: “All previ-\nous forms of society—or, what is the same, of the forces of social produc -\ntion—foundered on the development of wealth. Those thinkers of antiq -\nuity who were possessed of consciousness therefore directly denounced \nwealth as the dissolution of the community.”27\nThe Political Economy of Communal Society\n“All treatises on political economy,” Marx and Engels wrote, “take private \nproperty for granted.”28 In opposition to this and in line with Hegel, Marx \ninsisted that “all production is appropriation of nature on the part of an \nindividual within and through a specific form of society. In this sense it is \na tautology to say that property (appropriation) is a precondition of produc-\ntion,” while to claim that production is identical with private property is to \ndeny the greater part of human history. Communal production and prop-\nerty constituted the “natural economy” of society, which had prevailed at \na low level of the development of the productive forces. Private property \nemerged with class society and the division of labor, only becoming the \ndominant property form under capitalist relations of production.29\n“Property,” Marx wrote in the Grundrisse, “originally means—in its Asiat -\nic, Slavonic, ancient classical, Germanic form—the relation of the working \n52 MONTHLY REVIEW / J ULY –A UGUST  2025\n\n(producing or self-reproducing) subject to the conditions of his production \nor reproduction as his own.” Here he meant by the “Asiatic” form primar-\nily the village communities in India and Java; by the “Slavonic” form, the \nRussian mir, or peasant commune, which still persisted in the nineteenth \ncentury; by the “ancient classical” form, the communal relations still evi-\ndent in the Greek polis; and by the Germanic form, the old Mark tradition, \nin which the commune was reflected in German tribes “ coming-together” \nperiodically on a collective basis, while not “being-together.”30 Marx also re-\nferred to communal property as evidenced in the Celts. Tacitus wrote in \nhis Germania with respect to the Germanic tribes: “Lands proportioned to \ntheir own number are appropriated in turn for tillage by the whole body \nof tillers. They then divide them among themselves according to rank; \nthe division is made easy by the wide tracts of cultivable ground available. \nThe ploughlands are changed yearly, and still there is enough to spare.”31 \nIt was recognized that in many communal societies, “the individual has \nno property as distinct from the commune, but rather is merely its posses-\nsor,” under principles of communal usufruct. A part of the surplus labor \ninvariably goes to the “higher community” for its reproduction.32 In such \nsituations, “membership in the commune remains the presupposition for \nthe appropriation of land and soil, but, as a member of the commune, the \nindividual is a private proprietor” of a “particular plot.”33\nIn both the Grundrisse and Capital, Marx laid great stress on Peruvian \ncommunal relations under the Incas. Based on Prescott’s work, Marx not-\ned that in Inca society an individual “had no power to alienate or add to \nhis possessions” with respect to the land, which was communally held \nand redistributed each year. In Capital, he referred to Peru under the Incas \nas having a “natural economy” or non-commodity economy, and to the \n“artificially developed communism of the Peruvians.” What fascinated \nMarx with respect to Peru was that it was a “society in which the highest \nforms of economy, e.g. cooperation, a developed division of labor, etc.” \nwere “found even though there [was] no kind of money” and a “com -\nmunity of labour.” In some other social formations, such as the Slavic \ncommunities, Marx emphasized that while monetary exchange occurred \nin external relations it was not “at the centre of communal society as the \noriginal constituent element.” Even in the Roman Empire at its highest \ndevelopment, the “money system” only dominated in the army.34\nMarx considered the “Asian communal system” represented by still-exist-\ning village communities to be one of the main exemplars of the “original \nunity” between workers and the natural conditions of production. He in-\nsisted that “a whole collection of diverse patterns (though sometimes only \nremnants survive) [of ‘primitive communal property’] remained in existence \nM ARX  & C OMMUNAL  S OCIETY  53\n\nin India, where “communal labour” could be seen in “its spontaneously \nevolved form.” Indeed, “a careful study of Asiatic, particularly Indian, forms \nof communal property ownership would indicate that the disintegration \nof different forms of primitive communal ownership gives rise to diverse \nforms of property. For instance, prototypes of Roman and German private \nproperty can be traced back to certain forms of Indian communal property.” \nThe Asiatic form of property in village communities represented a form \n(theoretically) anterior to the ancient Greek and Roman mode.35 In Marx’s \nanalysis of precapitalist economic formations, Hobsbawm noted, “the ori-\nental [Asiatic] (and Slavonic) forms are historically closest to man’s origins, \nsince they conserve the functioning primitive (village) community in the \nmidst of the more elaborate social superstructure, and have an insufficient-\nly developed class system.”36\nIt is often said that Marx and Engels laid strong emphasis on the idea \nof an “Asiatic mode” of production, which is usually described, relying \nmore on Karl Wittfogel than on Marx, as a society in which the need for \nlarge irrigation projects, and thus vast collective labor, led to the growth \nof a centralized, despotic state, or a hypertrophy of the state. There is \nlittle basis for this in Marx, however. Although Marx employed the no -\ntion of an Asiatic mode in the preface to his 1859 Contribution to Political \nEconomy, he almost never used the term and eventually dropped it alto -\ngether. Moreover, while Marx referred on occasion to a despotic state \nmanaging large irrigation projects, his analysis was generally directed \nat the village communities themselves, which he saw as self-sustaining \ncollectives exhibiting communal ownership, production, and exchange \nboth in agriculture and small manufacture (artisanal production).37 These \nIndian village communities, which he explicitly identified with “primi -\ntive communism,” exhibited a tenacity of existence that pointed to an \nantiquity even greater than the “ancient commune and state” of Greece \nand Rome. Moreover, unlike ancient Greece and Rome, slavery did not \nlie at the economic foundation of Asiatic society. 38 Although such soci -\neties often took a despotic tributary form, this did not negate for Marx \nthe communal nature of property/production in the village communities \nthemselves. Nevertheless, despotism from above, together with coloniza-\ntion, often led to their stagnation in terms of mere simple reproduction.39\nThe economic nature of communal production and exchange, Marx indi-\ncated in the Grundrisse, lay in its attention to collective human needs, and \nthe development of the social individual. “The communal character of \nproduction would make the product into a communal, general product, \nfrom the outset” not mediated by commodity exchange. “The exchange \nwhich originally takes place in production…would not be an exchange \n54 MONTHLY REVIEW / J ULY –A UGUST  2025\n\nof exchange values but of activities” and use values. Such communal pro-\nduction/exchange would be “determined by communal needs and com -\nmunal purposes [and] would from the outset include the participation of \nthe individual in the communal world of products.” By its very nature, \ncommunal production is not determined post festum by the market, al -\nlowing capital to mediate all production relations, but rather ex ante on \ncommunal principles through which the social character of production is \npresupposed from the beginning.40 In this sense, production on the basis \nof communal property, in a modern context, he argued, would have to be \ncarried out “in accordance with a definite social plan,” one that “main -\ntains the correct proportion between the different functions of labour \nand the various needs of the associations” of workers.41\nIn capitalist society, according to Marx, “Time is everything, man is \nnothing; he is, at most, time’s carcase. Quality no longer matters. Quan-\ntity alone determines everything.” 42 In contrast, where communal pro -\nduction is concerned, labor time as pure quantity is crucial but does not \nhave the final say:\nThe determination of time remains, of course, essential. The less time the \nsociety requires to produce wheat, cattle, etc., the more time it wins for \nother production, material or mental. Just as in the case of an individual, \nthe multiplicity of its development, its enjoyment and its activity depends \non economization of time. Economy of time, to this all economy ultimate-\nly reduces itself. Society likewise has to distribute its time in a purpose -\nful way, in order to achieve a production adequate to its overall needs…. \nThus, economy of time, along with the planned distribution of labour time \namong the various branches of production, remains the first economic law \non the basis of communal production. It becomes law, there, to an even \nhigher degree. However, this is essentially different from a measurement \nof exchange values (labour or products) by labour time. The labour of in -\ndividuals in the same branch of work, and the various kinds of work, are \ndifferent from one another not only quantitatively but also qualitatively.43\nIt is true, Marx wrote to Engels in 1868, that “no form of society can pre-\nvent the labour time at the disposal of society from regulating production \nin ONE WAY OR ANOTHER. But so long as this regulation is a not effect -\ned through the direct and conscious control of society over its labour \ntime—which is only possible under common ownership—but through \nthe movement of commodity prices,” the result is the anarchy of capital-\nist class society and the failure to meet the “hierarchy of…needs.” Under \nthe generalized commodity economy of capitalism, the most pressing \nhuman and social needs—including the free development of the indi -\nvidual—rather than constituting the chief aims of production, become \nbarriers to accumulation.44\nM ARX  & C OMMUNAL  S OCIETY  55\n\nThe emergent productive power of labor as cooperation through which \nworkers become members of a “working organism” existed prior to cap-\nitalism. As Marx wrote in Capital, “simple co-operation,” which achieved \n“gigantic structures,” was evident in the colossal works of “the ancient \nAsiatics, Egyptians, Etruscans,” and, as he had noted elsewhere, in those \nof the Incas of Peru. Early civilizations in Asia “found themselves in pos -\nsession of a surplus which they could apply to works of magnificence or \nutility and in the construction of these their command over the hands \nand arms of almost the entire non-agricultural population has produced \nstupendous monuments which still indicate their power.”45 Such diverse \nnon-commodity societies were able to extract surplus as tribute from a \nlargely agricultural population. This conformed to the model of natural \neconomies, or what is now broadly called the tribute-paying or tribu -\ntary mode of production, which encompassed numerous precapitalist \ncivilizations from antiquity to feudalism, most of which retained com -\nmunal or collectivist relations at the base of society. 46 As Samir Amin \nremarked, “the tribute-paying mode,” emerged out of earlier “commu -\nnal modes of production.” It “adds to a still existing village community \na social and political apparatus for the exploitation of this community \nthrough the exaction of tribute.” Though it varied substantially in dif -\nferent times and places, it constituted “the most widespread form of \nprecapitalist societies.” 47\nFrom Medieval Commons/Communes to the Paris Commune \nof 1871\nUp to early modern times, peasant villages in Europe relied on custom-\nary rights in relation to the land, often accompanied by petty commodity \nproduction. Hence, the transition from feudalism to capitalism in Eu -\nrope, as in England beginning in the fifteenth century, depended on the \ndissolution of the customary rights and enclosure of the commons, there-\nby generating a modern proletariat—a process that took centuries. The \ncommons or communal property, even occurring within feudalism and \nother forms of tributary production, was associated with collective rights \nof appropriation while geared to use values and noncommodity forms of \nexchange. Whereas private property in a generalized commodity econo -\nmy is alienable, communal property in the land is not, and is rooted in \nthe customary rights of a particular community or locality. As histori -\nan Peter Linebaugh notes, “common rights are embedded in a particular \necology with its local husbandry.”48 In medieval society, peasant commu-\nnities had customary rights to the appropriation of the land/nature that \nplaced limits on the corresponding rights of the feudal lords to the land.\n56 MONTHLY REVIEW / J ULY –A UGUST  2025\n\nThe medieval commons of England are often thought of as simply having \nbeen based on the commons proper (woodlands, marshes, and uncultivat-\ned meadows used for grazing and for natural materials and resources), but \nthe commons in this narrow sense could not be separated from the com-\nmon fields themselves, directly surrounding the towns and villages, which \nwere normally kept in tillage through collective ploughing, with the strips \nof land distributed in such a way as to ensure the equality of villagers in \nthe access to the most fertile land.49 Marx wrote extensively in Capital and \nelsewhere on the enclosure of the commons as crucial to the development \nof capitalism, and the brutal means used in their forcible expropriation, \ncommenting on “the stoical peace of mind with which the political econo-\nmist regards the most shameless violation of the ‘sacred rights of property’ \nand the grossest acts of violence against persons, as soon as they are neces-\nsary in order to lay the foundations of the capitalist mode of production.”50\nThe notion of communal society has always been connected to the ques-\ntion of the political command structure of society as well as property/\nproduction, raising the issue of communal governance. In the late medie-\nval era, particularly in northern Italy and Flanders, there emerged urban \ncommunes or self-governing towns based on binding oaths between equal \n(usually wealthy) citizens in defiance of feudal notions of rank and vassal-\nage. The medieval urban communes were built around guilds and so took \nthe form of guild-based merchant oligarchies, forming the birthplace of \nthe bourgeoisie. The feudal era also generated utopian conceptions of ur-\nban communes, arising from a nascent bourgeoisie.51 The government of \nthe city of Paris following the storming of the Bastille in 1789 was known \nas the Paris Commune. It was from this earlier Paris Commune, emerging \nfrom a bourgeois revolution, that the revolutionary workers’ Paris Com-\nmune of 1871 was to take its name. 52 A far cry from the earlier medieval \ncommunes, and even from the Commune of Paris of 1789, the short-lived \nParis Commune of 1871, emerging during the Franco-Prussian War, repre-\nsented, according to Marx, not the construction of a new state power but \na negation of state power, and thus of the alienated dual relation of state \nand civil society. It constituted a genuine nineteenth-century revolution-\nary working-class urban communal order, which was to end after seven -\nty-two days in a massacre of the communards by the French state.\nFor Marx, the Paris Commune pointed to a new communal political com-\nmand structure that, in breaking with the capitalist state as a power above \nsociety nonetheless carried out functions analogous to it, still affected by \nthe bourgeois order from which it had emerged. Universal male suffrage \nwas introduced. Elected officials were to be paid at rates comparable to the \ngeneral workers’ wage, with the instant recall of those elected if they did \nM ARX  & C OMMUNAL  S OCIETY  57\n\nnot follow the mandates of their constituents. The Commune abolished \nthe death penalty, child labor, and conscription while eliminating debts. \nThe workers were organized into cooperative societies to run the factories, \nwith plans to organize the cooperatives into one big union. A women’s \nunion was created, as well as a system of universal secular education.53 As \nMarx wrote in The Civil War in France (1871):\nThe Commune intended to abolish that class property which makes the la-\nbour of the many the wealth of the few. It aimed at the expropriation of the \nexpropriators. It wanted to make individual property a truth by transform-\ning the means of production, land and capital, now chiefly the means of en-\nslaving and exploiting labour, into mere instruments of free and associated \nlabor.—But this is Communism, “impossible” Communism!…. [Indeed,] if \nco-operative production is not to remain a sham and a snare; if it is to su -\npersede the Capitalist system; if united co-operative societies are to regulate \nnational production upon a common plan, thus taking it under their own \ncontrol and putting an end to constant anarchy and periodical convulsions \nwhich are the fatality of Capitalist production—what else…would it be but \nCommunism, “possible” Communism?… This was the first revolution in \nwhich the working class was acknowledged as the only class capable of social \ninitiative…. The great social measure of the Commune was its own working \nexistence. Its special measures could but betoken the tendency of a govern-\nment of the people by the people…. Another measure of this [working] class \n[formation] was the surrender, to associations of workmen, under reserve of \ncompensation, of all closed workshops and factories, no matter whether the \nrespective capitalists had absconded, or preferred to strike work.54\nFor Marx, the Paris Commune, with all of its weaknesses, had proven that \nin a working-class republic, a state power above civil society was no longer \nnecessary along with the abolition of bourgeois civil society itself. The Paris \nCommune was an urban commune that prefigured a working-class republic \nas a whole based on collective production under a common plan and dem-\nocratic social governance, thereby constituting an initial phase in the tran-\nsition to a fuller communist society. “The Communal Constitution would \nhave restored to the social body all the forces hitherto absorbed by the State \nparasite feeding upon and clogging the free movement of society.”55\nThis overall view of the shaping of communal society, sharpened by \nthe experience of the Paris Commune, was reflected in Marx’s Critique of \nthe Gotha Programme, written in 1875. For Marx, the 1871 Paris Commune \nhad represented the form at last discovered of “the revolutionary dicta -\ntorship of the proletariat,” destined, he believed, to overthrow the class \ndictatorship of capital, constituting a new, more democratic order in the \ntransition to socialism/communism. In fully developed communism, as \nenvisioned by Marx and Engels, there would be no Leviathan of state pow-\ner standing above society. The state would gradually “wither away” as the \n58 MONTHLY REVIEW / J ULY –A UGUST  2025\n\npolitical command structure was transferred to the population at large, \nreplaced by what Engels called simply community/commune.56 Nor would \nthere be civil society in the bourgeois sense. The economy would be run \non a common plan in which decisions would be made principally ex ante \nby the associated producers, not post festum by the market. Creative labor, \nwould be “the prime necessity of life” such that “the free development \nof each” would become the basis of “the free development of all.” The \noverall structure of the economy would be that of a “co-operative society \nbased on common ownership of the means of production” and governed \nby the principle from each according to one’s ability, to each according to one’s \nneed. “Within the co-operative society based on common ownership of \nthe means of production, the producers do not exchange their products…\nsince now, in contrast to capitalist society, individual labour no longer ex-\nists in an indirect fashion but directly as a component part of the total la-\nbour.” In such a society, “communal satisfaction of needs, such as schools, \nhealth services, etc.” would be vastly increased in proportion, as would the \nrealm of cultural development generally. The “sources of life,” that is, the \nland/nature, would be made into common property for the benefit of all.57\nIn delimiting the overall character of production, Marx wrote in Capital: \n“Freedom, in this sphere [determined by natural necessity], can only consist \nin this, that socialised man, the associated producers, govern the human \nmetabolism with nature in a rational way…accomplishing it with the least \nexpenditure of energy,” in the process of promoting sustainable human de-\nvelopment.58 The alienated social metabolism between humanity and na-\nture would be transcended. As Marx had indicated early on in his Economic \nand Philosophical Manuscripts, “communism, as fully developed naturalism, \nequals humanism, and as fully developed humanism equals naturalism; it is \nthe genuine resolution of the conflict between man and nature.”59\nThe Revolution in Ethnological Time\nThe year 1859 saw the publication of both Charles Darwin’s On the Origin \nof Species, which provided a strong theory of natural evolution for the first \ntime, and a closely related “revolution in ethnological time,” resulting \nfrom the discovery of prehistorical human remains in Brixham Cave in \nSouthwestern England. The Brixham Cave discovery expanded the length \nof time in which human beings were recognized to have lived on Earth \nby thousands of centuries. Human remains, sometimes accompanied by \nprimitive instruments, had been found prior to this, including the first \nNeanderthal remains in the Neanderthal Valley in Germany in 1856. Al -\nthough less spectacular than the Neanderthal discovery, the Brixham \nCave remains left no doubt about “the great antiquity of mankind.”60\nM ARX  & C OMMUNAL  S OCIETY  59\n\nThe result was a great rush to explore the evolutionary and anthropo -\nlogical origins of human beings, the nature of early societies, and the \norigins of the family, the state, and private property, in such works as \nThomas Huxley’s Evidences as to Man’s Place in Nature (1863); Charles Lyell’s \nGeological Evidences of the Antiquity of Man (1863); John Lubbock’s Pre-historic \nTimes (1864); Henry Sumner Maine’s Village-Communities in the East and West \n(1871); Lewis Henry Morgan’s Ancient Society (1877); and John Budd Phear’s \nThe Aryan Village in India and Ceylon  (1880). In Germany, Georg Ludwig von \nMaurer continued the research that he had commenced in 1854 with his \ngreat work on the German Mark, Introduction to the History of the Mark, Vil -\nlage, and Town Constitutions and Public Power.\nIn 1880–1882, Marx composed a series of excerpts from the works of \nMorgan, Phear, Maine, and Lubbock, known as his Ethnological Notebooks. \nHe had taken extensive notes a year earlier from the ethnological studies \nof the young Russian sociologist Maxim Kovalevsky, whose book man -\nuscript, Communal Landownership: The Causes, Course and Consequences of Its \nDissolution, dealt with communal relations in India, Algeria, and Latin \nAmerica.61 In 1880–1881, he took down passages from William B. Money’s \nJava; or How to Manage a Colony (1861).\nThe source of Marx’s interest in ethnological studies at the end of his \nlife was best indicated by his response to Maurer’s work on the German \nMark, in which Maurer had conclusively demonstrated that the Mark \nhad a stronger communal basis than was previously thought. Writing \nto Engels in 1868, Marx indicated that these ethnological investigations \nof Maurer and others revealed, unknowingly on their part, that it was \ncrucial “to look beyond the Middle Ages into the primitive age of every \nnation, and that [this] corresponds to the socialist trend.” Nevertheless, \nMaurer and other similar ethnological investigators, such as the philolo -\ngist and cultural historian Jakob Grimm, Marx remarked, showed no real \ncomprehension of this tendency: “They are then surprised to find what \nis newest in what is oldest.” The surviving communal forms, remnants \nfrom more egalitarian communities of the past, pointed in a dialectical \nway to the future developed communist society.62\nGiven his previous close studies of communal property and communal \ngovernance in societies, Marx was able to incorporate these new discov -\neries in all their richness without fundamentally altering his basic ap -\nproach, developed over his life. In his Ethnological Notebooks, the focus is of-\nten on communal relations. Twenty-seven passages from Morgan’s Ancient \nSociety addressing communal property, housing, and land tenure are high-\nlighted by Marx with parallel lines drawn next to them in the margins or \nwith brief comments.63 Still, much more emphasis than in Marx’s earli -\n60 MONTHLY REVIEW / J ULY –A UGUST  2025\n\ner work was placed here on kinship-based and gender relations, as they \nshaped these communities. He was particularly impressed by Morgan’s \nstudies of the Haudenosaunee, called the Iroquois Confederacy by the \nFrench and the League of the Five Nations by the English, representing \nan earlier clan-based (gens-based) society. “All members of the Iroquois \ngens,” Marx wrote, drawing on Morgan, were “ personally free, bound to \ndefend each other’s freedom.”64 The Haudenosaunee built large longhouses \nthat included multiple families. The longhouses were described by Mor -\ngan in his Houses and House-Life of the American Aborigines  (1881), as “large \nenough to accommodate, five, ten, and twenty families, and each house -\nhold practiced communism in living.”65 In Morgan’s words, as excerpted \nand emphasized by Marx: “It (a higher plan of society) will be a revival, in \na higher form, of the liberty, equality and fraternity of the ancient gentes \n[traditional communal society].”66\nMarx’s understanding of property as arising originally from appropri -\nation of nature removed the myth of peoples without property used to \njustify the expropriation of the land by European colonists. In his inter -\npolated extracts from Kovalevsky’s Communal Landownership with respect \nto Algeria, Marx (via Kovalevsky) observed that “centuries of Arabic, Turk-\nish, finally French rule, except in the most recent period…were unable to \nbreak up the consanguineal [kinship-based] organization, and the principles \nof indivisibility and inalienability of landownership.”67 Yet, only a revolt could \nsecure lasting communal land tenure. Following two months spent in Al-\ngiers in 1882 for his health, Marx was to declare that the Algerians “will go \nto rack and ruin WITHOUT A REVOLUTIONARY MOVEMENT.”68 Likewise, \nhe was to take special note via his excerpts from Kovalevsky of the British \n“robbery of the communal and private property of the peasants” in India.69\nDue to ill health, Marx was unable in these last years prior to his death \nin 1883 to develop a treatise, as he had clearly intended, based on his Ethno-\nlogical Notebooks. However, Engels sought to carry Marx’s ethnological dis-\ncoveries via Morgan, Maurer, and others forward in his Origins of the Family, \nPrivate Property, and the State (1884), written in the year after Marx’s death, \nas well as in The Mark (1882), which Marx read and commented on prior \nto publication. Engels’s analysis was deeply rooted in the examination of \nkinship and gender relations, particularly the gens (clan) as it manifested \nitself in different cultures. Everywhere—in the Iroquois in North America, \nin the Incas in Peru, in the village communities in India and Java, in the \nRussian obshchina, in Celtic clans in Europe, in Greek antiquity, and in \nthe German Mark—there were indications, he argued, of large household \ncommunities, common living, common land tenure, common tillage, and \ncooperative labor, varying over time and location. Aspects of these archaic \nM ARX  & C OMMUNAL  S OCIETY  61\n\ncommunal relations were evident in the ancient Greek phratry and the \nRoman gens.70 “The patriarchal household community,” he declared,\nwas widespread, if not universal, as the intermediate stage between the \nmother-right communistic family and the modern isolated family…. The \nquestions whether their economic unit was the gens or the household \ncommunity or an intermediate communistic kinship group, or whether all \nthree of these groups existed depending on land conditions will remain \nsubject of controversy for a long time yet. But Kovalevsky maintains that \nthe conditions described by Tacitus presuppose not the Mark or village com-\nmunity, but the household community; only this latter developed, much \nlater into the village community, owing to the growth of population.71\nIn Engels’s conception, in the earliest, most traditional, hunter and \ngatherer tribal societies, where an economic surplus did not yet exist, the \nsocial order was centered more on the reproduction of kinship relations \nand of the population than on production in the economic sense.72\nThe contemporary issue of the Russian commune, which played an im-\nportant part in Marx and Engels’s thought, first arose in 1847–1852. It was \nat that time that the Prussian Baron von Haxthausen-Abbenburg (a German \naristocrat and official and supporter of serfdom) wrote a study of Russian \nagrarian relations with the support of the tsar, in which he uncovered the \nwidespread existence of the Russian mir (obshchina). This discovery was to \nplay a big role in the development of Russian populism. At first, Marx saw \nnothing particularly distinctive in the Russian mir, viewing it as simply a \nmanifestation of a decaying archaic communal order. However, upon re-\nceiving a copy of The Situation of the Working Class in Russia by the young Rus-\nsian scholar V. V. Bervi (Flerovskii) in 1869, Marx devoted himself with the \nutmost urgency to learning to read Russian, which he achieved in less than \na year. This led him to the intensive study of Russian populism, which end-\ned up changing his views about the contemporary significance of the mir.73\nMarx’s developed view of the Russian commune was manifested in the \n1881 drafts of his letter to Vera Zasulich, and in the 1882 preface (written \ntogether with Engels) to the second Russian edition of The Communist Mani-\nfesto. In his draft letters to Zasulich, Marx argued that the Russian mir was \nthe most developed form of communal agriculture, traces of which had \nbeen found “everywhere” in Europe, and in parts of Asia. Earlier forms, \nsuch as the German tribes at the time of Caesar, were kinship-based and \ncharacterized by communal living and collective cultivation. In contrast, \nthe later agrarian commune of the German Mark, as described by Tacitus \nmore than a century later, combined village communal ownership, includ-\ning the periodic redistribution of the land, with individual homes and cul-\ntivation. The agrarian commune displayed a “dualism” in forms of proper-\n62 MONTHLY REVIEW / J ULY –A UGUST  2025\n\nty that was both a source of greater vitality and also a sign of impending \ndissolution and the gradual emergence of private property, in which the \nremaining communal property would become merely an appendage.74\nAll of the surviving forms in the lineage of communal agriculture, to be \nfound in Russia and in Asia in the nineteenth century (in the former, free \nfrom the distorting force of external colonization), exhibited the same \nfundamental characteristics and dualism of the agrarian commune. Wher-\never agrarian communism had survived, it was due to its existence as a \n“localised microcosm” that was subjected to “a more or less centralized des-\npotism above the commune.” All of this raised the question as to wheth-\ner the Russian commune or mir could be the basis for the development \nof a new communist society. Marx’s tentative answer was that given: (1) \nthe non-kinship basis of the Russian commune; (2) its “contemporane -\nity,” which meant that it was able to incorporate some of the “positive \nachievements of the capitalist system without having to pass under its \nharsh tribute”; and (3) its survival on a national basis, it could conceivably \nbe the nucleus of a newly developed communal society, rooted in cooper-\native labor. The crisis of contemporary capitalist society could itself pro -\nmote “the return of modern societies to a higher form of an ‘archaic’ type \nof collective ownership of production.” But for this to happen, a revolu -\ntion would be necessary drawing on contemporary socialist movements.75\nMarx and Engels concluded their preface to the second Russian edition \nof The Communist Manifesto with the words: “If the Russian Revolution be-\ncomes the signal for proletarian revolution in the West, so that the two \ncomplement each other, then Russia’s peasant communal land-owner -\nship may serve as the point of departure for a communist development.”76\nCommunal Society as Past and Future\nMarx indicated several times over the course of his life that the sur -\nvival of remnants of communal landownership in the region surround -\ning Trier, where he grew up, had left a deep impression on him. He had \ndiscussed these archaic property relations in his youth with his father, \na lawyer. His translation of Tacitus’s Germania, completed while Marx \nwas still in his teens, no doubt reinforced these views. His early studies \nof the Greek polis and philosophy via Aristotle and Epicurus (both of \nwhom addressed the nature of community); his engagement as editor \nof the Rheinische Zeitung  with the question of the peasantry’s loss of \ncustomary rights to the forest; and his adoption of Hegel’s notion of ap -\npropriation/property as the basis of society all fed into this perspective. \nProperty, for Marx, writing in 1842, arose from “the elemental power of \nnature” and human labor. This was visible in the Germany of his day in \nM ARX  & C OMMUNAL  S OCIETY  63\n\nthe customary/communal right to gather wood from the forest, in line \nwith all forms of appropriation basic to human existence. 77\nMarx’s approach to the question of communism from the beginning \nwas materialist and historical, emphasizing the social origins of human be -\nings, as opposed to the individualist, idealist, Romantic, and utopian views \ncommon among French socialists and German Young Hegelians. From his \nearliest writings, he stressed the natural, communal basis of human appro-\npriation from nature and the social development of property relations as \na product of human labor evident throughout human history, contrasting \nthis to the alienated relations of capitalist private property. This involved a \ndeeply anthropological view and a labor theory of culture.78 The resulting \nsocial ontology underpinned his entire critique of political economy. The \nnotion that the past offered clues to the human future, and the possibility \nof transcending the present through the creation of a higher communal \nsociety, governed Marx’s thought almost from the beginning.\nDue to the underlying importance of communal society in Marx’s thought, \nhe drew on all the historical and anthropological information available in \nhis time to explore the various forms of communal property and commu-\nnal governance, including both agrarian communes and urban communal \nstructures. He dug deeply into Greek and Roman history, reports of colonial \nadministrators, and early ethnological works. This research was carried for-\nward by other classical Marxists, particularly Rosa Luxemburg.79 Ultimately, \nMarx was convinced that the past mediated between the present and the \nfuture. The natural, spontaneously communal basis of humanity would be \nresurrected in a higher form of society, not just in Europe, but worldwide \nvia revolution. “No misinterpretation of Marx,” Hobsbawm wrote, “is more \ngrotesque than the one which suggests that he expected a revolution exclu-\nsively from the advanced industrial countries of the West.”80\nIn our time, the revolutions in China, with its early, vibrant People’s \nCommunes and its current system of collective land tenure in commu -\nnities, and in Venezuela, with its diverse communes and its struggle to \ncreate a “communal state,” demonstrate that the human future, if there \nis to be one at all, requires the creation of a communal society, a society \nof, by, and for the associated producers.81\nNotes\n1. R. N. Berki, Insight and Vision: The \nProblem of Communism in Marx’s \nThought (London: J. M. Dent, 1983), 1.\n2. Paresh Chattopadhyay, Marx’s As -\nsociated Mode of Production  (London: \nPalgrave Macmillan, 2016).\n3. On Marx and Epicurus, see John \nBellamy Foster, Breaking the Bonds of \nFate: Epicurus and Marx  (forthcoming, \nMonthly Review Press).\n4. Karl Marx and Frederick Engels, Col-\nlected Works  (New York: International \nPublishers, 1975), vol. 1, 215–23; Moses \nHess, The Holy History of Mankind and \nOther Writings (Cambridge: Cambridge \nUniversity Press, 2004); David McLellan, \nKarl Marx: His Life and Thought (New York: \nHarper and Row, 1973), 47–56.\n64 MONTHLY REVIEW / J ULY –A UGUST  2025\n\n5. Moses Hess, “Speech on Commu -\nnism, Elberfeld, 15 February 1845,” \nMarxists Internet Archive, marxists.\norg; Lucretius 5.1136; Aristotle, Politics \nI.1253a; Patricia Springborg, “Marx, \nDemocracy and the Ancient Polis,” Crit-\nical Philosophy  1, no. 1 (1984): 52. In \nreferring to man as a “political animal,” \nAristotle meant a member of a polis, that \nis, society, particularly a town.\n6. Jean-Jacques Rousseau, The “Dis -\ncourses” and Other Early Political Writings \n(Cambridge: Cambridge University Press, \n2019), 165; Pierre-Joseph Proudhon, \nWhat Is Property?  ( C a m b r i d g e :  C a m-\nbridge University Press, 1993), 13–16, 70.\n7. G. W. F. Hegel, The Philosophy of Right \n(Oxford: Oxford University Press, 1952), \n41–42. On property as appropriation in \nclassical political economy (as in John \nLocke), see C. B. Macpherson, The Polit-\nical Theory of Possessive Individualism  \n(Oxford: Oxford University Press, 1962), \n194–262; John Locke, Two Treatises of \nGovernment ( C a m b r i d g e :  C a m b r i d g e  \nUniversity Press, 1988), 297–301.\n8. Karl Marx, Capital, vol. 1 (London: \nPenguin, 1976), 647.\n9. Marx, Collected Works, vol. 1, 17.\n10. Marx and Engels, Collected Works, \nvol. 26, 168.\n11. Karl Marx and Frederick Engels, \nSelected Correspondence  (Moscow: \nProgress Publishers, 1975), 189; Karl \nMarx, “Marx-Zasulich Correspondence: \nLetters and Drafts,” in Late Marx and the \nRussian Road , ed. Teodor Shanin (New \nYork: Monthly Review Press, 1983), 118; \nKevin B. Anderson, The Late Marx’s Rev -\nolutionary Roads (London: Verso, 2025), \n70. On the German Mark, see Frederick \nEngels, “The Mark,” in Engels, Socialism: \nUtopian and Scientific  (New York: Inter -\nnational Publishers, 1989), 77–93.\n12. Marx and Engels, Collected Works, \nvol. 1, 254; Daniel Bensaïd, The Dispos-\nsessed: Karl Marx’s Debates on Wood \nTheft and the Rights of the Poor  (Min -\nneapolis: University of Minnesota Press, \n2021). On such customary rights in the \nEnglish context in the eighteenth centu-\nry, see E. P . Thompson, Customs in Com-\nmon (New York: The New Press, 1993).\n13. Eric Hobsbawm, Introduction to \nKarl Marx, Pre-Capitalist Economic For -\nmations (New York: International Pub -\nlishers, 1964), 21.\n14. Editors’ note, in Marx and Engels, \nCollected Works , vol. 35, 773. Marx \nwas to rely in Capital on such works \nas George Campbell, Modern India: A \nSketch of the System of Civil Govern -\nment (London: John Murray, 1852) and \nT. Stamford Raffles, The History of Java \n(London: John Murray, 1817).\n15. Thomas R. Trautmann, Lewis Henry \nMorgan and the Invention of Kinship  \n(Berkeley: University of California Press, \n1987), 3.\n16. Marx and Engels, Collected Works, \nvol. 29, 461.\n17. Karl Marx, Grundrisse (London: Pen-\nguin, 1973), 495; Marx and Engels, Col-\nlected Works, vol. 5, 32–33. The question \nof “mother right” or of traditional matri -\nlineal society was only introduced later by \nEngels in The Origin of the Family, Private \nProperty and the State , based primarily \non Lewis Henry Morgan’s Ancient Society \nand Marx’s Ethnological Notebooks.\n18. Karl Marx, Theories of Surplus Value \n(Moscow: Progress Publishers, 1975), \npart 3, 422–23; Frederick Engels, “Sup -\nplement to Volume Three of Capital,” in \nKarl Marx, Capital, vol. 3 (London: Pen -\nguin, 1981), 1038; Marx and Engels, \nCollected Works , vol. 47, 103. Engels \nexpanded the concept of “primitive \ncommunism” to the precursors of the \nGermanic Mark association, as well as to \nthe village communities in India and the \nRussian commune or mir (obshchina) in \nhis day. The inclusion of precursors of \nthe German Mark in this context was \nprobably what accounted for his own \nvery provisional substitution of the term \n“primitive communism” (in his appen -\ndix to Capital and a couple of letters) for \nthe Asiatic mode as characterizing the \nbase mode of production in such societ-\nies. Engels refrained altogether from al -\nluding to earlier hunting and gathering \nsocieties, as “primitive communism,” \nseeing these societies as determined \nlargely by kinship relations rather \nthan economics. Nevertheless, neither \nMarx nor Engels had any doubt about \nthe communal-clan character of these \nearlier societies, which was reinforced \nin the 1870s and ’80s by their anthro -\npological writings: Marx’s Ethnological \nNotebooks and Engels’s Origins of the \nFamily, Private Property, and the State . \nSee Stephen P . Dunn, “The Position of \nthe Primitive-Communal Social Order in \nthe Soviet-Marxist Theory of History,” in \nToward a Marxist Anthropology, ed. Stan-\nley Diamond (Berlin: De Gruyter, 2011), \n175, 181; Moses Finley, “ Ancient Soci -\nety,” in A Dictionary of Marxist Thought , \ned. Tom Bottomore et al. (Oxford: Black-\nwell, 1983), 20.\n19. Marx and Engels, Collected Works, \nvol. 5, 33.\n20. Karl Marx, Ethnological Notebooks, \ned. Lawrence Krader (Assen, Nether -\nlands: Van Gorcum, 1974), 292; Marx, \nGrundrisse, 474–75, 477, 483.\n21. Springborg, “Marx, Democracy and \nthe Ancient Polis,” 52–53.\n22. Karl Marx, Early Writings  (London: \nPenguin, 1974), 90; Hegel, The Philos -\nophy of Right, 183; Marx, Capital, vol. 3, \n970; Karl Polanyi, Primitive, Archaic and \nModern Economies  (Boston: Beacon \nPress, 1971), 82–83.\n23. Marx, Grundrisse, 103, 491, 495–96; \nMarx, Ethnological Notebooks, 213; Marx \nand Engels, Collected Works, vol. 5, 332; \nMarx, Capital, vol. 3, 970; Springborg, \n“Marx, Democracy and the Ancient Po -\nlis,” 59; Finley, “Ancient Society,” 20. As \nSamir Amin notes, slavery “is practically \nnowhere found to be the origin of class \ndifferentiation.” Samir Amin, Unequal De-\nvelopment: An Essay on the Social Forma-\ntions of Peripheral Capitalism (New York: \nMonthly Review Press, 1976), 20. Coin -\nage appeared in China about the same \ntime as in Lydia (or earlier). See “Chinese \nCoinage,” American Numismatic Associa-\ntion, n.d., money.org\n24. Marx, Capital, vol. 3, 245; Perry An-\nderson, Passages from Antiquity to Feu -\ndalism (London: New Left Books, 1974), \n18, 35. G. E. M. de Ste. Croix’s great \nwork, The Class Struggle in the Ancient \nGreek World (London: Duckworth, 1981) \ncan be seen as aligned with Anderson in \nthis respect. In contrast, see Ellen Meik -\nsins Wood, Peasant-Citizen and Slave  \n(London: Verso, 1989), 42–80. Wood \nargued that, aside from domestic ser -\nvice and work in silver mines, two areas \nwhere slave labor predominated, the \nremaining enslaved people in ancient \nAthens were “scattered through the divi-\nsion of labour,” including areas such as \nagriculture and the “lower civil service,” \nas in the “Scythian archers who repre -\nsented the nearest thing to an Athenian \npolice force.” Wood, Peasant-Citizen and \nSlave, 79.\n25. Marx, Grundrisse, 245, 491, 495–\n96; Marx, Ethnological Notebooks, 213; \nMarx and Engels, Collected Works, vol. \n5, 332; Springborg, “Marx, Democracy \nand the Ancient Polis,” 59; Finley, “ An-\ncient Society ,” 20. On the tribal forma -\ntion in Attica, see George Thomson, The \nPrehistoric Aegean: Studies in Ancient \nM ARX  & C OMMUNAL  S OCIETY  65\n\nGreek Society  (London: Lawrence and \nWishart, 1978), 104–9.\n26. This has now been established in \ngreat detail in contemporary classical \nscholarship. See Richard Seaford, Mon-\ney and the Early Greek Mind: Homer, \nPhilosophy, Tragedy (Cambridge: Cam -\nbridge University Press, 2004), 1–20, \n125–36, 147–72.\n27. Marx, Grundrisse, 540.\n28. Marx and Engels, Collected Works, \nvol. 4, 31–32.\n29. Marx, Grundrisse, 87–88, 488–89.\n30. Marx, Grundrisse, 483, 495. In re -\nlation to Java, Marx was influenced by \nThomas Stamford Raffles’s 1817 History \nof Java. Marx, Capital, vol. 1, 417, 916; \nRaffles, History of Java.\n31. Tacitus, Germania, 26; translation as \nfound in Tacitus, The Agricola and the Ger-\nmania, trans. H. Mattingly and S. A. Hand-\nford (London: Penguin, 1970), 122–23.\n32. Marx, Grundrisse, 473–75.\n33. Marx, Grundrisse, 473–75; Spring -\nborg, “Marx, Democracy, and the An -\ncient Polis,” 56.\n34. Marx, Grundrisse, 102–3, 473, 490; \nKarl Marx, Capital, vol. 2 (London: Pen -\nguin, 1978), 196, 226; Marx, Capital, \nvol. 3, 1017; William H. Prescott, History \nof the Conquest of Mexico/History of the \nConquest of Peru  (New York: Modern \nLibrary, n.d.; originally published sepa -\nrately in 1843/1847), 756–57.\n35. Marx, Theories of Surplus Value , \nPart 3, 422–23; Karl Marx, A Contribu -\ntion to the Critique of Political Economy  \n(Moscow: Progress Publishers, 1970), \n21, 33; Marx, Grundrisse, 490–95.\n36. Hobsbawm, Introduction to Marx, \nPre-Capitalist Economic Formations , \n37–38.\n37. Marx’s concept of the “Asiatic mode of \nproduction, ” a term which he almost never \nused directly (though he made frequent \nreference to Asiatic village communities), \nhad the virtue of going against any uni -\nlinear theory of development, raising the \nissue of alternative paths. He saw it as \nstanding for the oldest form of commu -\nnal property, which, like the related Slavic \nform, was remarkable for its tenacity. He \nwas eventually to conclude that the Rus-\nsian commune (as well as perhaps some \nAsiatic village communities) could con -\nceivably be the basis of revolutionary de-\nvelopments when integrated with modern \ncommunist thought, possibly skirting the \ncapitalist path. See Marx, Theories of Sur-\nplus Value, part 3, 422–23; Lawrence Krad-\ner, The Asiatic Mode of Production: Sources, \nDevelopment and Critique in the Writings \nof Karl Marx  (Assen, Netherlands: Van \nGorcum and Co., 1975), 5–7, 183; John \nBellamy Foster and Hannah Holleman, \n“Weber and the Environment, ” American \nJournal of Sociology 117, no. 6 (2012): \n1640–41; Bryan S. Turner, “ Asiatic Society, ” \nin A Dictionary of Marxist Thought, 32–36; \nKarl Wittfogel, “Geopolitics, Geographical \nMaterialism and Marxism,” Antipode 1 7 ,  \nno. 1 (1985): 21–71.\n38. Marx, Grundrisse, 470–73; Marx, \nTheories of Surplus Value , Part 3, 422; \nMarx, Pre-Capitalist Economic Forma -\ntions, 69–70, 88; Marx and Engels, Col-\nlected Works, vol. 25, 149–50.\n39. It is a mistake to argue, as Kevin \nAnderson does, that Marx was mainly \ninterested in “communal social forma -\ntions” as a whole, and that “communal \nproperty” was “too superficial a category \nfor his investigations.” Rather, Marx al -\nways based his analysis in this sphere \non communal property, often found \nin forms that were in contradiction to \nthe larger tributary formation. Nor is it \nmeaningful to claim that many tradi -\ntional societies “lack much in the way \nof property,” since property itself for \nMarx (and Hegel) is merely derivative \nof forms of appropriation that lie at the \nbasis of human material existence in all \nof its forms. Hence, no society can be \ndevoid of property. Anderson, The Late \nMarx’s Revolutionary Roads, 8–19.\n40. Marx, Grundrisse, 171–72.\n41. Marx, Capital, vol. 1, 171–72.\n42. Marx and Engels, Collected Works, \nvol. 6, 127; István Mészáros, Beyond \nCapital (New York: Monthly Review \nPress, 1995), 765.\n43. Marx, Grundrisse, 172–73; \nMészáros, Beyond Capital, 749. The no -\ntion of “time’s carcase” here has to do \nwith Epicurus’s conception of time as \nthe accident of accidents, “death the im-\nmortal,” erasing all qualitative features. \nMarx, Collected Works , vol. 1, 63–65; \nMarx, Collected Works, vol. 6, 166.\n44. Marx and Engels, Collected Works, \nvol. 42, 515; Karl Marx, Texts on Method, \ned. Terrell Carver (Oxford: Basil Black -\nwell, 1975), 195.\n45. Marx, Capital, vol. 1, 451–53.\n46. On the concept of “natural econo -\nmy” in Marx and Rosa Luxemburg, see \nScott Cook, Understanding Commodity \nEconomies (New York: Rowman and Lit -\ntlefield, 2004), 114, 130–31, 151; Rosa \nLuxemburg, The Accumulation of Cap -\nital (New York: Monthly Review Press, \n1951), 368–85.\n47. Amin, Unequal Development , \n13–20.\n48. Peter Linebaugh, The Magna Carta \nManifesto (Berkeley: University of Cali -\nfornia Press, 2008), 44–45.\n49. Jan de Vries, The Economy of Eu -\nrope in an Age of Crisis, 1600–1750  \n(Cambridge: Cambridge University \nPress, 1976), 43; Christopher Dyer, “The \nEconomy and Society,” in Oxford Illus -\ntrated History of Medieval England , ed. \nNigel Saul (Oxford: Oxford University \nPress, 1997), 143–46; Thomas Edward \nScrutton, Commons and Common Fields \n(Cambridge: Cambridge University \nPress, 1887), 1; John Bellamy Foster, \nBrett Clark, and Hannah Holleman, \n“Marx and the Commons,” Social Re -\nsearch 88, no. 1 (Spring 2021): 1–5.\n50. Marx, Capital, vol. 1, 889. See Ian \nAngus, The War Against the Commons: \nDispossession and Resistance in the \nMaking of Capitalism (New York: Month-\nly Review Press, 2023).\n51. See Jan Dumolyn and Jelle Haemers, \nCommunes and Conflict: Urban Rebellion \nin Late Medieval Flanders , eds. Andrew \nMurray and Joannes van den Maagden-\nberg (Boston: Brill, 2023), 229–49.\n52. Mitchell Abidor, “The Paris Commune: \nMyth Made Material, ” Tocqueville21, May \n11, 2021, tocqueville21.com.\n53. Mathijs van de Sande and Gaard \nKets, “From the Commune to Commu -\nnalism,” Resilience, March 22, 2021, \nresilience.org.\n54. Karl Marx and Frederick Engels, \nWritings on the Paris Commune , ed. \nHal Draper (New York: Monthly Review \nPress, 1971), 76–81.\n55. Marx and Engels, Writings on the \nParis Commune , 75; Frederick Engels \nin Karl Marx, Critique of the Gotha Pro -\ngramme (New York: International Pub -\nlishers, 1938), 31.\n56. Marx and Engels, Collected Works, \nvol. 25, 247–48, 267–68; V. I. Lenin, The \nState and Revolution (Moscow: Progress \nPublishers, 1969), 16–27. On the whole \nquestion of the “withering away of the \nstate,” see Mészáros, Beyond Capital , \n460–95.\n57. Marx, Critique of the Gotha Pro -\ngramme, 5–10, 31; Karl Marx and \nFrederick Engels, The Communist Man -\n66 MONTHLY REVIEW / J ULY –A UGUST  2025\n\nifesto (New York: Monthly Review Press, \n1964), 41.\n58. Marx, Capital, vol. 3, 959.\n59. Marx, Early Writings, 348.\n60. Trautmann, Lewis Henry Morgan \nand the Invention of Kinship , 3; Lewis \nHenry Morgan, Ancient Society, ed. Elea-\nnor Burke Leacock (New York: Merdian \nBooks, 1963); Preface to John Bella -\nmy Foster, Marx’s Ecology  (New York: \nMonthly Review Press, 2000), 212–13.\n61. Karl Marx, “Excerpts from M. M. \nKovalevsky,” in Krader, The Asiatic Mode \nof Production, 346–414.\n62. Karl Marx to Frederick Engels, \nMarch 25, 1868, in Marx and Engels, \nSelected Correspondence, 188–89.\n63. Lawrence Krader, Introduction to \nMarx, Ethnological Notebooks, 28.\n64. Marx, Ethnological Notebooks, 150.\n65. Lewis Henry Morgan, Houses and \nHouse Lives of the American Aborigines  \n(Chicago: University of Chicago Press, \n1965), 6.\n66. Marx, Ethnological Notebooks , 81, \n139; Morgan, Ancient Society, 562.\n67. Marx, “Excerpts from M. M. Kovalev-\nsky,” 400.\n68. Karl Marx to Laura Lafargue, April \n13, 1882, Collected Works, vol. 46, 242; \nPeter Hudis, “Marx Among the Mus -\nlims,” Capitalism Nature Socialism  15, \nno. 4 (2004): 67.\n69. Marx, “Excerpts from M. M. Kovalev-\nsky,” 387. See John Bellamy Foster, Brett \nClark, and Hannah Holleman, “Marx and \nthe Indigenous,” Monthly Review 71, no. \n9 (February 2020): 9–12.\n70. Marx and Engels, Collected Works, \nvol. 26, 167–68, 190–203; Marx and \nEngels, Collected Works , vol. 6, 482; \nFrederick Engels, “The Mark,” in Fred -\nerick Engels, Socialism: Utopian and \nScientific (New York: International Pub -\nlishers, 1989), 77–93. Engels’s “The \nMark” is often referred to as first having \nappeared as an appendix to the 1892 \nedition of Socialism: Utopian and Scien-\ntific, but it was initially published in the \nfirst German edition of Socialism: Utopi-\nan and Scientific in 1882. Engels sent it \nto Marx prior to publication requesting \nsuggested changes. Although Marx had \nearlier taken notes on the Teutonic Mark \nin his Ethnological Notebooks based on \nMaurer’s discussion, it was Engels’s “The \nMark” and Marx’s comments in this re -\nspect in his draft letters to Vera Zasulich \nthat represented their most developed \nview, an area in which they were in close \naccord. Marx and Engels, Selected Corre-\nspondence, 334.\n71. Marx and Engels, Collected Works, \nvol. 26, 241–42. Engels’s Origin of the \nFamily, Private Property, and the State  \nis often dismissed for its supposed rig -\nid notion of “primitive communism.” \nThus, anthropologist David Graeber \nand archaeologist David Wengrow in \nThe Dawn of Everything  use this as an \nexcuse for dismissing Engel’s analysis, \ndespite the fact that Engels himself \nnever used the term “primitive commu -\nnism” in his book , which was imported \ninto historical materialism in this con -\ntext by Second and Third International \nMarxism. Nor did Engels ever apply \nthe term “primitive communism” to \nhunting and gathering societies, which \nhe saw through a much more complex \nkinship lens, though recognizing “com -\nmunal” elements. The main outlines \nof Engels’s argument, focusing on kin -\nship, community, and egalitarianism in \ntraditional societies, conforms to what \nanthropology in general has long since \ndiscovered in this respect. Having foist -\ned the notion of some kind of absolute, \npure, and holistic “primitive commu -\nnism” on Engels, Graeber and Wen -\ngrow proceed to declare that property \nrelationships were more “ambiguous” \nthan Engels thought. They emphasize \nthe gendered division of labor, as if this \ninvalidates Engels’s argument, ignoring \nhis own analysis there. Nevertheless, the \nexistence of communal property and \nrelatively egalitarian arrangements in \nhunting and gathering societies and in \nmany later societies is not to be denied. \nHence, Graeber and Wengrow them -\nselves point to a “baseline communism” \nsupposedly in opposition to Engels’s \ndogmatic (though in fact nonexistent) \nuse of “primitive communism” to de -\nscribe hunting and gathering societies. \nDavid Graeber and David Wengrow, The \nDawn of Everything: A New History of \nHumanity (New York: Farrar, Straus and \nGiroux, 2021), 47. For a more detailed \ndiscussion of Engels’s Origin of the \nFamily, Private Property, and the State , \nemphasizing kinship-family-gender as -\npects of his argument, see John Bellamy \nFoster, The Return of Nature  (New York: \nMonthly Review Press, 2020), 287–96. \nOn the egalitarian character of tradition-\nal kinship societies and their collective/\ncommunal aspects, see Morton Fried, \nThe Evolution of Political Society: An Es -\nsay on Political Anthropology (New York: \nRandom House, 1967); Richard B. Lee, \n“Reflections on Primitive Communism,” \nin Hunters and Gatherers , eds. Tim In -\ngold, David Riches, and James Wood -\nburn (New York: Berg, 1988), 252–68.\n72. Marx and Engels, Collected Works, \nvol. 26, 131–32; Dunn, “The Position of \nPrimitive-Communal Order in the Sovi -\net-Marxist Theory of History,” 180–81.\n73. Haruki Wada, “Marx and Revolu -\ntionary Russia,” in Shanin, Late Marx and \nthe Russian Road, 43–45.\n74. Marx, “Marx-Zasulich Correspon -\ndence,” 103, 107–9, 118–20.\n75. Marx, “Marx-Zasulich Correspon -\ndence,” 110–13, 120–21.\n76. Karl Marx and Frederick Engels, \n“Preface to the Second Russian Edition \nof the Manifesto of the Communist Par -\nty” (1882), in Late Marx and the Russian \nRoad, ed. Shanin, 139.\n77. Marx and Engels, Collected Works, \nvol. 1, 234.\n78. Charles Woolfson, The Labour \nTheory of Culture: A Re-Examination of \nEngels’s Theory of Human Origins  (Lon-\ndon: Routledge and Kegan Paul, 1982); \nMarx and Engels, Collected Works, vol. \n25, 452–64.\n79. Rosa Luxemburg, Complete Works, \nvol. 1, ed. Peter Hudis (London: Verso, \n2014), 146–234.\n80. Hobsbawm, Introduction to Marx, \nPre-Capitalist Economic Formations, 49.\n81. On China, see William Hinton, \nFanshen: A Documentary of Revolution \nin a Chinese Village  (New York: Month -\nly Review Press, 2008) and Lu Xinyu, \n“‘Chinese-Style Modernization’: Revo -\nlution and the Worker-Peasant Alliance,” \nMonthly Review  76, no. 9 (February \n2025): 22–41. On Venezuela, see John \nBellamy Foster, “Chávez and the Com -\nmunal State,” Monthly Review  66, no. \n11 (April 2015): 1–17; and Chris Gilbert, \nCommune or Nothing!: Venezuela’s \nCommunal Movement and Its Social -\nist Project  (New York: Monthly Review \nPress, 2023).\nM ARX  & C OMMUNAL  S OCIETY  67\n\nReproduced with permission of copyright owner.\nFurther reproduction prohibited without permission.	Marx and Communal Society\nJOHN BELLAMY FOSTER\n“Ultimately communism is the only thing that is important about [Karl] \nMarx’s thought,” Hungarian British political theorist R. N. Berki observed \nin 1983.1 Although this was an exaggeration, it is undeniable that Marx’s \nbroad conception of communal society/communism formed the basis of \nhis entire critique of class society and his vision of a viable future for hu-\nmanity. Yet, there have been few attempts to engage systematically with \nthe develop...	en	0.9	completed	11644	73872	2025-08-27 21:26:52.132007	2025-08-27 21:26:52.43664	\N	1	\N	\N
\.


--
-- Data for Name: domains; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.domains (id, uuid, name, display_name, namespace_uri, description, metadata, is_active, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: experiment_documents; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.experiment_documents (experiment_id, document_id, added_at) FROM stdin;
\.


--
-- Data for Name: experiment_references; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.experiment_references (experiment_id, reference_id, include_in_analysis, added_at, notes) FROM stdin;
\.


--
-- Data for Name: experiments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.experiments (id, name, description, experiment_type, configuration, status, results, results_summary, created_at, updated_at, started_at, completed_at, user_id) FROM stdin;
\.


--
-- Data for Name: extracted_entities; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.extracted_entities (id, entity_text, entity_type, entity_subtype, context_before, context_after, sentence, start_position, end_position, paragraph_number, sentence_number, confidence_score, extraction_method, properties, language, normalized_form, created_at, updated_at, processing_job_id, text_segment_id) FROM stdin;
\.


--
-- Data for Name: fuzziness_adjustments; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.fuzziness_adjustments (id, term_version_id, original_score, adjusted_score, adjustment_reason, adjusted_by, created_at) FROM stdin;
\.


--
-- Data for Name: ontologies; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.ontologies (id, uuid, domain_id, name, base_uri, description, is_base, is_editable, parent_ontology_id, ontology_type, metadata, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: ontology_entities; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.ontology_entities (id, ontology_id, entity_type, uri, label, comment, parent_uri, domain, range, properties, embedding, created_at) FROM stdin;
\.


--
-- Data for Name: ontology_mappings; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.ontology_mappings (id, ontology_uri, concept_label, concept_definition, parent_concepts, child_concepts, related_concepts, mapping_confidence, mapping_method, mapping_source, semantic_type, domain, properties, is_verified, verified_by, verification_notes, alternative_mappings, created_at, updated_at, verified_at, extracted_entity_id) FROM stdin;
\.


--
-- Data for Name: ontology_versions; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.ontology_versions (id, ontology_id, version_number, version_tag, content, content_hash, change_summary, created_by, created_at, is_current, is_draft, workflow_status, metadata) FROM stdin;
\.


--
-- Data for Name: processing_jobs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.processing_jobs (id, job_type, job_name, provider, model, parameters, status, progress_percent, current_step, total_steps, result_data, result_summary, error_message, error_details, retry_count, max_retries, tokens_used, processing_time, cost_estimate, created_at, started_at, completed_at, updated_at, user_id, document_id, parent_job_id) FROM stdin;
7	generate_embeddings	\N	\N	\N	{"embedding_method": "local"}	completed	0	\N	\N	{"embedding_method": "local", "embedding_dimensions": 384, "chunk_count": 117, "processing_time": 2.5}	\N	\N	\N	0	3	\N	\N	\N	2025-08-27 21:27:29.993994	\N	\N	2025-08-27 21:27:29.999072	1	61	\N
\.


--
-- Data for Name: provenance_chains; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.provenance_chains (id, entity_id, entity_type, was_derived_from, derivation_activity, derivation_metadata, created_at) FROM stdin;
\.


--
-- Data for Name: search_history; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.search_history (id, query, query_type, results_count, execution_time, user_id, ip_address, created_at) FROM stdin;
\.


--
-- Data for Name: semantic_drift_activities; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.semantic_drift_activities (id, activity_type, start_period, end_period, temporal_scope_years, used_entity, generated_entity, was_associated_with, drift_metrics, detection_algorithm, algorithm_parameters, started_at_time, ended_at_time, activity_status, drift_detected, drift_magnitude, drift_type, evidence_summary, created_by, created_at) FROM stdin;
\.


--
-- Data for Name: term_version_anchors; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.term_version_anchors (id, term_version_id, context_anchor_id, similarity_score, rank_in_neighborhood, created_at) FROM stdin;
5d96a7a6-5998-4cf8-bb0f-89b35192b251	703b355f-e602-40ad-a470-33a89d008dd8	e52c0e9a-c7b1-43c1-9db8-1e2be5f7af1a	\N	\N	\N
3d23291a-f7b7-498c-b7a1-d7635177ab4a	703b355f-e602-40ad-a470-33a89d008dd8	99267944-387f-4c8d-a0ba-62bbc69d2f4d	\N	\N	\N
359ba9c5-69ec-401c-a200-48e52b65bede	703b355f-e602-40ad-a470-33a89d008dd8	0bd2bb6f-36f3-46cf-9b60-d7ab53b77fa5	\N	\N	\N
6d216341-693d-4cde-b0a0-c613ee9a75f3	703b355f-e602-40ad-a470-33a89d008dd8	03406a50-523c-43c3-aeb4-e151c60f442a	\N	\N	\N
\.


--
-- Data for Name: term_versions; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.term_versions (id, term_id, temporal_period, temporal_start_year, temporal_end_year, meaning_description, context_anchor, original_context_anchor, fuzziness_score, confidence_level, certainty_notes, corpus_source, source_documents, extraction_method, generated_at_time, was_derived_from, derivation_type, version_number, is_current, created_by, created_at, neighborhood_overlap, positional_change, similarity_reduction, source_citation) FROM stdin;
703b355f-e602-40ad-a470-33a89d008dd8	8ca94d22-caec-4b8c-81e1-205d8cd5a0bb	2025	\N	\N	a usually young man who engages in rowdy or violent behavior especially as part of a group or gang : ruffian, hoodlum	["hooligan", "usually", "young", "engages"]	\N	\N	medium	\N	\N	\N	manual	2025-08-24 14:03:22.101585-04	\N	\N	1	t	1	2025-08-24 14:03:22.102248-04	\N	\N	\N	Merriam-Webster.com Dictionary, s.v. "hooligan," accessed August 24, 2025, https://www.merriam-webster.com/dictionary/hooligan.
\.


--
-- Data for Name: terms; Type: TABLE DATA; Schema: public; Owner: ontextract_user
--

COPY public.terms (id, term_text, entry_date, status, created_by, updated_by, created_at, updated_at, description, etymology, notes, research_domain, selection_rationale, historical_significance) FROM stdin;
8ca94d22-caec-4b8c-81e1-205d8cd5a0bb	hooligan	2025-08-24 14:03:22.10073-04	active	1	\N	2025-08-24 14:03:22.100732-04	2025-08-24 14:03:22.100733-04	\N	\N			\N	\N
\.


--
-- Data for Name: text_segments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.text_segments (id, content, segment_type, segment_number, start_position, end_position, parent_segment_id, level, word_count, character_count, sentence_count, language, language_confidence, embedding, embedding_model, processed, processing_notes, topics, keywords, sentiment_score, complexity_score, created_at, updated_at, processed_at, document_id) FROM stdin;
2310	Ethical Decision-Making Theory: An Integrated Approach\nMark S. Schwartz 1\nReceived: 15 December 2014 / Accepted: 23 September 2015 / Published online: 26 October 2015\n/C211 Springer Science+Business Media Dordrecht 2015\nAbstract Ethical decision-making (EDM) descriptive\ntheoretical models often conﬂict with each other and typ-\nically lack comprehensiveness. To address this deﬁciency,\na revised EDM model is proposed that consolidates and\nattempts to bridge together the varying and sometimes\ndirectly conﬂicting propositions and perspectives that have\nbeen advanced. To do so, the paper is organized as follows.\nFirst, a review of the various theoretical models of EDM is\nprovided. These models can generally be divided into\n(a) rationalist-based (i.e., reason); and (b) non-rationalist-\nbased (i.e., intuition and emotion). Second, the proposed\nmodel, called ‘Integrated Ethical Decision Making,’ is\nintroduced in order to ﬁll the gaps and bridge the current\ndivide in EDM theory. The individual and situational fac-\ntors as well as the process of the proposed model are then\ndescribed. Third, the academic and managerial implica-\ntions of the proposed model are discussed. Finally, the\nlimitations of the proposed model are presented.\nKeywords Emotion /C1Ethical decision making /C1\nIntuition /C1Moral rationalization /C1Moral reasoning\nIntroduction\nWhile much has been discovered regarding the ethical\ndecision-making (EDM) process within business organi-\nzations, a great deal remains unknown. The importance of\nEDM is no longer in doubt, given the extent of illegal and\nunethical activity that continues to take place every year\nand the resultant costs to societal stakeholders including\nshareholders, employees, consumers, and the natural\nenvironment (U.S. Sentencing Commission 2014; Asso-\nciation of Certiﬁed Fraud Examiners 2014). Unethical\nactivity by individuals continues despite the best efforts of\nbusiness organizations to implement comprehensive ethics\nprograms, including codes of ethics, ethics training, and\nwhistleblowing hotlines (Ethics Resource Center 2014;\nWebley 2011) and despite the extent to which business\nschools around the world teach the subject of business\nethics (Rossouw and Stu ¨ ckelberger 2012). The signiﬁcant\nnegative yet potentially preventable costs to society\nresulting from the unethical actions of individual ﬁrm\nagents suggest that ethical decision making might be\nconsidered one of the most important processes to better\nunderstand, not only for the academic management ﬁeld,\nbut also for the corporate community and society at large\n(Trevin˜o 1986).\nThere have however been important developments\nthrough academic research over recent years leading to an\nimproved understanding of EDM (see Trevin ˜o et al. 2006;\nTenbrunsel and Smith-Crowe 2008) including how to\nmeasure each of its constructs and dimensions (Agle et al.\n2014). Building on and borrowing from a series of aca-\ndemic disciplines and theories including moral philoso-\nphy, moral psychology, social psychology, social\neconomics, organizational behavior, criminology, behav-\nioral science, behavioral ethics, cognitive neuroscience,\nand business ethics, a number of descriptive EDM theo-\nretical models have been proposed to help explain the\ndecision-making process of individuals leading to ethical\nor unethical behavior or actions (see Torres 2001).\nCommonly referred to as EDM theory, these descriptive\n& Mark S. Schwartz\nschwartz@yorku.ca\n1 School of Administrative Studies, Faculty of Liberal Arts and\nProfessional Studies, York University, 4700 Keele Street,\nToronto, ON M3J 1P3, Canada\n123\nJ Bus Ethics (2016) 139:755–776\nDOI 10.1007/s10551-015-2886-8	paragraph	1	0	3672	\N	0	526	3672	28	en	\N	\N	\N	f	\N	\N	\N	\N	\N	2025-08-27 20:36:49.630247	2025-08-27 20:36:49.63025	\N	59
2311	theoretical EDM frameworks (as opposed to normative\nEDM frameworks) help to explain how cognitive pro-\ncesses (i.e., reason or intuition) or affective processes\n(i.e., emotion) operate within the brain (Reynolds 2006a;\nSalvador and Folger 2009; Greene et al. 2001) leading to\nmoral judgment and behavior on the part of individuals.\nTo further enhance our understanding, these theoretical\nmodels typically present the EDM process as a series of\ntemporal and sequential process stages, typically begin-\nning with initial awareness or recognition of an ethical\nissue leading to a moral judgment, intention to act, and\nﬁnally to behavior (Rest 1984, 1986).\n1\nIn addition to explaining the EDM process, most theo-\nretical EDM models also include a set of individual, orga-\nnizational, or situational-related variables and indicate at\nwhich stage of EDM (i.e., awareness, judgment, intention,\nor behavior) they can exert a causal effect or a moderating\ninﬂuence. Based on these theoretical EDM models, hun-\ndreds of empirical studies, both qualitative and quantitative\nin nature, along with several meta-studies, have now been\nconducted to try to verify and explain exactly which inde-\npendent factors or variables actually inﬂuence the decision\nmaking of individuals, including whether one stage of EDM\nnecessarily leads to the next stage (see Ford and Richardson\n1994; Loe et al. 2000; O’Fallon and Butterﬁeld 2005; Craft\n2013; Lehnert et al. 2015).\nWhile such theoretical and empirical research has\nproven helpful to better understand what has been referred\nto as the ‘black box’ of EDM (Liedka 1989, p. 805;\nTenbrunsel and Smith-Crowe 2008, p. 584), the relevance\nor explanatory power of the theoretical and empirical\nresearch can at least initially be questioned given the lack\nof consistent ﬁndings (O’Fallon and Butterﬁeld 2005;\nCraft 2013; Pan and Sparks 2012). This may be partially\nattributable due to the research methods being used (e.g.,\nthe use of scenarios/vignettes, surveys, student samples,\nor self-reporting, see Randall and Gibson 1990; O’Fallon\nand Butterﬁeld 2005) or the diversity or quality of the\nresearch measurement instruments being utilized (see\nMudrack and Mason 2013; Casali 2011). Another possi-\nbility may be that EDM is simply too complex a neuro-\ncognitive-affective process involving too many inter-re-\nlated or undiscoverable variables being processed by our\nbrains preventing any possible generalizable conclusions.\nIt may also be that the predictive ability of any theoretical\nEDM model will be limited to activity that more clearly\nconstitutes ethical or unethical behavior, rather than pre-\ndicting behavior involving more complex ethical dilem-\nmas where achieving normative consensus over what even\nconstitutes ‘ethical’ behavior can often prove to be\nelusive.\n2 The challenges and complexity of EDM have\neven led some researchers to suggest a ‘punch bowl’ or\n‘garbage can’ approach to EDM, which assumes that\nresearchers will never know exactly what takes place\nleading to ethical judgments in that only what goes into or\nout of the process is capable of being analyzed (e.g.,\nSchminke 1998, p. 207).\nOne other possible explanation for the lack of consistent\nempirical ﬁndings however is that further reﬁnements to\nEDM descriptive theory models if undertaken might\nimprove the models’ explanatory and predictive capability\nleading to more relevant and consistent empirical ﬁndings.\nIt is this latter possibility that this paper seeks to address.\nFor example, a review of the descriptive EDM theoretical\nmodels proposed to date (Tenbrunsel and Smith-Crowe\n2008) along with consideration of the more recent chal-\nlenges and criticisms raised with respect to EDM research\n(Haidt 2001; Sonenshein 2007; Whittier et al. 2006;B a r -\ntlett 2003) suggests that there is signiﬁcant room for\nimprovement in theoretical EDM models. Following their\nreview of the empirical EDM research, O’Fallon and\nButterﬁeld state ( 2005, p. 399): ‘‘If the ﬁeld of descriptive\nethics is to move forward to strengthen our understanding\nof the EDM process, it is imperative that future studies\nfocus more attention on theory development.’’ According\nto Tenbrunsel and Smith-Crowe ( 2008, p. 547): ‘‘ …many\n[studies] are still atheoretical or uni-theoretical, relying on\na single theory.’’ They then reﬂect on the deﬁciency in\nEDM theory: ‘‘Unlike in the past, researchers no longer\nneed to justify their rationale for studying ethics; instead,\ntheir attention needs to focus on developing a more com-\nprehensive theoretical platform upon which empirical work\nin behavioral ethics can continue’’ (Tenbrunsel and Smith-\nCrowe 2008, p. 593). In other words, the current dis-\nagreement among scholars over which theoretical EDM\nmodel (if any) is the most appropriate, especially when\nengaging in empirical research, needs to be addressed.\nThis paper will attempt to contribute to EDM literature\nby focusing on the primary gaps in the theoretical EDM\nmodels that have been identiﬁed. By doing so, the research\nobjective is to develop a theoretical EDM model that not\nonly captures and builds upon the current state of EDM, but\nalso consolidates and attempts to bridge together the vary-\ning and sometimes directly conﬂicting propositions and\nperspectives that have been advanced. In other words, the\npaper will attempt to incorporate and depict what has not\nalways been clearly portrayed in any proposed EDM model\nin a more integrated manner. The most important or key\nintegration being advanced is the combined and inter-\n1 For ease of reference, ‘ethics’ or ‘ethical’ are considered throughout\nthe paper to be synonymous with ‘morality’ or ‘moral.’\n2 For example, Ferrell and Gresham state ( 1985, p. 87): ‘ ‘Absence of\na clear consensus about ethical conduct …has resulted in much\nconfusion among academicians …’’\n756 M. S. Schwartz\n123	paragraph	2	3674	9519	\N	0	909	5845	44	en	\N	\N	\N	f	\N	\N	\N	\N	\N	2025-08-27 20:36:49.630252	2025-08-27 20:36:49.630253	\N	59
2312	related impact of intuition–emotion along with reason–ra-\ntionalization on the moral judgment stage of EDM. In\naddition, to address the proliferation of individual, organi-\nzational, and situational/issue-related factors being applied\nin EDM research, several core constructs are proposed in\norder to better capture their corresponding sub-variables,\nsuch as an individual’s ‘moral capacity’ and an organiza-\ntion’s ‘ethical infrastructure.’ Other important features of\nthe revised model include (i) the presence of ‘lack of moral\nawareness’ leading to behavior; (ii) the expansion of the\nissue-based EDM variable; (iii) the inclusion of moral\nrationalization; and (iv) the addition of an explicit ‘moral\nconsultation’ stage into the EDM process.\nThe proposed integrated model essentially reﬂects a\nsynthesis of the ‘intuitionist/sentimentalist’ (Haidt 2001),\n‘rationalist’ (Kohlberg 1973; Rest 1986), ‘person-situation\ninteractionist’ (Trevin˜o 1986), and ‘issue-contingent’ (Jones\n1991) approaches to EDM. The revised model attempts to\ndepict the current theoretical ﬁeld of EDM in a relatively\ncomprehensive yet hopefully more coherent and simpliﬁed\nmanner. The intended contribution of the proposed model is\nnot necessarily to offer any particularly new major insights\ninto EDM, but to depict a theoretical platform and schematic\nrepresentation upon which a broader range of EDM\nresearchers, including both rationalists and non-rationalists,\ncan hopefully feel comfortable utilizing in a more cohesive\nand consistent manner. In addition, while ‘is’ does not\nnecessarily imply ‘ought,’ the development of a more robust\ndescriptive EDM model may lead to more effective and\nrelevant normative EDM models which might then have an\neffect on future management or educational practices.\nIn order to propose and depict a reformulated theoretical\nEDM model, the paper will be organized as follows. First, a\nreview of the various theoretical models of EDM will be\nprovided. These models can generally be divided into\n(a) rationalist-based (i.e., reason); and (b) non-rationalist-\nbased (i.e., intuition and emotion). Second, the proposed\nmodel, called ‘Integrated EDM’ (I-EDM), is introduced in\norder to ﬁll the gaps and bridge the current divide in EDM\ntheory. The individual and situational factors as well as the\nprocess of the proposed model are then described. Third,\nthe academic and managerial implications of the proposed\nmodel will be discussed. Finally, the limitations of the\nproposed model are presented.\nSeveral notes of caution are required however. This\nstudy is not intended to provide a comprehensive literature\nreview of the EDM ﬁeld. Only what might be considered to\nbe the most salient or utilized EDM models or research is\nincluded in the discussion.\n3 In addition, each of the EDM\nconstructs or processes is not discussed to the same extent,\nrather those that require modiﬁcation from previous EDM\nmodels are given greater emphasis throughout the paper. In\naddition, the unit of analysis is individuals acting within or\non behalf of business organizations, rather than organiza-\ntional-level ethical decision making.\nFinally, for the purposes of the paper, a few key deﬁ-\nnitions are required. An ethical dilemma is deﬁned as a\nsituation in which an individual must reﬂect upon com-\npeting moral standards and/or stakeholder claims in\ndetermining what is the morally appropriate decision or\naction.\n4 Moral judgment is deﬁned as the determination of\nthe ethically appropriate course of action among potential\nalternatives. Ethical behavior is deﬁned not merely as\nconforming to the legal or moral norms of the larger\ncommunity\n5 (Jones 1991), but consists of behavior sup-\nported by one or more additional moral standards. 6\nReview of the Theoretical Descriptive EDM\nApproaches\nA review of EDM research reveals that there are two\ngeneral categories of EDM theoretical models, those that\nare (a) rationalist-based; and (b) non-rationalist-based. 7\nThe rationalist-based models speciﬁcally assume that the\n3 This is similar to the approach used by Trevin ˜o et al. ( 2006) in their\nliterature review of EDM.\n4 One might try to distinguish situations involving ‘ethical dilemmas’\nfrom those whereby an individual is facing a ‘moral temptation.’\n‘Ethical dilemmas’ can be seen as those more challenging situations\ninvolving ‘right versus right’ or ‘wrong versus wrong’ alternatives,\nsuch as deciding which employee to lay off. ‘Moral temptations’\nhowever involve ‘right versus wrong’ alternatives more directly\nlinked to one’s self-interest, such as deciding whether to steal supplies\nfrom the ofﬁce supply cabinet (see Kidder 1995). For the purposes of\nthe I-EDM model, both ethical dilemmas and moral temptations can\nbe faced by individual decision makers as ethical issues.\n5 Jones states ( 1991, p. 367): ‘‘ …an ethical decision is deﬁned as a\ndecision that is both legal and morally acceptable to the larger\ncommunity. Conversely, an unethical decision is either illegal or\nmorally unacceptable to the larger community.’’ This is too limited a\ndeﬁnition of ‘ethical’ to be utilized for the purposes of properly\nstudying the EDM process. Jones ( 1991, p. 367) himself admits that\nhis deﬁnition of an ethical decision is ‘‘imprecise and relativistic’’ and\nrefers to the difﬁculties of establishing substantive deﬁnitions for\nethical behavior. Others have also suggested that this deﬁnition of\nwhat is ethical is ‘ ‘too relativistic’’ and avoids a precise normative\nposition on right versus wrong (Reynolds 2008; Tenbrunsel and\nSmith-Crowe 2008). In addition, community norms can violate\n‘hypernorms’ (see Donaldson and Dunfee 1999).\n6 While there is an extensive literature on moral theory, the moral\nstandards can be grouped under three general categories: (i) conven-\ntionalist (e.g., industry or corporate codes of ethics); (ii) consequen-\ntialist (e.g., utilitarianism); or (iii) deontological, including\ntrustworthiness, respect, moral rights, and justice/fairness (see\nSchwartz and Carroll 2003; Schwartz 2005).\n7 Another possible way of dividing up EDM models is to categorize\nthose that focus primarily on the disposition of the decision maker,\nversus those that are more interactional (person-situation) in nature.\nSee Tsang ( 2002, p. 25).\nEthical Decision-Making Theory: An Integrated Approach 757\n123	paragraph	3	9521	15848	\N	0	952	6327	51	en	\N	\N	\N	f	\N	\N	\N	\N	\N	2025-08-27 20:36:49.630254	2025-08-27 20:36:49.630255	\N	59
2313	moral reasoning process dominates the core of the model,\nleading to moral judgment. The non-rationalist-based\nmodels assume that both intuition and emotion dominate the\nmoral judgment process, with moral reasoning playing a\nsecondary ‘after the fact’ explanatory (i.e., reason) or jus-\ntiﬁcatory (i.e., rationalization) role for one’s moral judg-\nment (Haidt 2001; Sonenshein 2007). More recent models\nhowever suggest that rather than reason–rationalization and\nintuition–emotion being mutually exclusive, there is either\na ‘dual-process’ involving two stages or a ‘two-systems’\nprocess whereby there is concurrent interaction between\nintuition (impulsive) and reason (reﬂective) leading to\nmoral judgment (see Reynolds 2006a; Strack and Deutsch\n2004) or between emotion and reason leading to moral\njudgment (Greene et al. 2001). These interactions form the\nbasis of the revised model discussed below. Each group of\nEDM theoretical models will now be brieﬂy outlined.\nRationalist approaches\nThe ﬁrst group of theoretical models explicitly or implicitly\nassumes that a predominantly reason-based process takes\nplace leading to moral judgment. The rationalist approach\nsuggests that upon experiencing an ethical dilemma, the\ndecision maker attempts to resolve conﬂicts through a\nlogical, rational and deliberative cognitive process by\nconsidering and weighing various moral standards that\nmight be in conﬂict with one another. The vast majority of\nempirical EDM researchers appear to rely on this particular\ntheoretical framework when conducting their research.\nFor example, Ferrell and Gresham ( 1985) developed a\n‘multistage contingency’ model of EDM, in which an eth-\nical dilemma arises from the social or cultural environment.\nThe behavior of the decision maker is then affected by two\nsets of ‘contingency factors’ including (1) individual factors\n(i.e., knowledge, values, attitudes, and intentions); and (2)\norganizational factors (i.e., signiﬁcant others including top\nmanagement and peers, and opportunity including codes,\nenforcement, and rewards and punishment).\n8\nTrevin˜o( 1986) introduces a ‘person-situation interaction-\nist’ model of ethical decision making. Her model begins by\nsuggesting that the manner by which an ethical dilemma is\nanalyzed by the decision maker depends upon the individual’s\nstage of cognitive moral development (Kohlberg 1973).\n9 The\ndecision maker’s initial cognition of right and wrong is then\nmoderated by individual factors including ego strength\n(strength of conviction or self-regulating skills), ﬁeld depen-\ndence (dependence on external social referents), and locus of\ncontrol (perception of how much control one exerts over the\nevents in life). Situational factors also moderate behavior such\nas immediate job context (reinforcement contingencies such\nas rewards and punishment for ethical/unethical behavior) and\nother external pressures (including personal costs, scarce\nresources, or competition). Organizational culture (normative\nstructure, referent others, obedience to authority, and\nresponsibility for consequences) and characteristics of the\nwork also moderate behavior.\nPossibly the most signiﬁcant or prominent rationalist-\nbased theoretical model of EDM is by Rest ( 1986), who\nposited that there are four distinct process components (or\nstages) of EDM: (1) becoming aware that there is a moral\nissue or ethical problem or that the situation has ethical\nimplications (also referred to as ‘interpreting the situation,’\n‘sensitivity,’ or ‘recognition’)\n10; (2) leading to a moral\njudgment (also referred to as ‘moral evaluation,’ ‘moral\nreasoning,’ or as ‘ethical decision making’) 11; (3) estab-\nlishing a moral intent (also referred to as moral ‘motiva-\ntion,’ ‘decision,’ or ‘determination’)12; and (4) then acting\non these intentions through one’s behavior (also referred to\nas ‘implementation’ or ‘action’). 13 The moral judgment\nstage of Rest’s model which is the key moral reasoning\ncomponent of the EDM process is based on Kohlberg’s\n(1973) rationalist theory of moral development.\nJones ( 1991) provided an important contribution to\nEDM theory by not only building on and consolidating\nprevious theoretical EDM models such as Rest ( 1986), but\nby including an important new factor, the nature of the\n8 Ferrell et al. ( 1989) later suggest a revised ‘synthesis model’ which\nincorporates into their original model (1985) Kohlberg’s stages of\nmoral development as well as the deontological and teleological\nmoral evaluation process taken from Hunt and Vitells’ EDM model\n(1986).\n9 Kohlberg ( 1973) proposed three general levels of moral develop-\nment including the pre-conventional (stage one: punishment; stage\ntwo: self-interest), conventional (stage three: referent others; stage\nfour: law), and post-conventional (stage ﬁve: social contract; stage\nFootnote 9 continued\nsix: universal ethical principles). Kohlberg in later years indicated\nthat his model focused on moral reasoning, and later clariﬁed that it\nreally only focused on justice/fairness issues. See Rest et al. ( 1999).\n10 For ‘heightened ethical concern,’ see De Cremer et al. ( 2010, p. 3).\nMoral awareness is deﬁned by Rest ( 1986, p. 3) as the ‘ ‘ …interpre-\ntation of the particular situation in terms of what actions (are)\npossible, who (including oneself) would be affected by each course of\naction, and how the interested parties would regard such effects on\ntheir welfare.’’\n11 Moral judgment is deﬁned by Rest as: ‘‘[F]iguring out what one\nought to do. Applying moral ideals to the situation to determine the\nmoral course of action’ ’ (Rest 1984, p. 26).\n12 For ‘determination’ see Ferrell et al. ( 1989, p. 60). Moral intention\nmight be considered synonymous with moral motivation which Rest\ndeﬁnes as giving ‘ ‘ …priority to moral values above other personal\nvalues such that a decision is made to intend to do what is morally\nright’’ (1986, p. 3).\n13 Moral action is deﬁned as having ‘‘ …sufﬁcient perseverance, ego\nstrength, and implementation skills to be able to follow through on\nhis/her intention to behave morally, to withstand fatigue and ﬂagging\nwill, and to overcome obstacles’’ (Rest 1986, pp. 4–5).\n758 M. S. Schwartz\n123	paragraph	4	15850	22025	\N	0	924	6175	50	en	\N	\N	\N	f	\N	\N	\N	\N	\N	2025-08-27 20:36:49.630256	2025-08-27 20:36:49.630257	\N	59
2314	ethical issue itself. Jones ( 1991, p. 367) states that an ethical\nissue exists when a person’s actions, when freely performed\n(i.e., involve a choice) ‘ ‘ …may harm or beneﬁt others.’’\nJones deﬁnes the ‘moral intensity’ of the ethical issue as a\nconstruct that ‘ ‘…captures the extent of [the] issue-related\nmoral imperative in a situation’ ’ ( 1991, p. 372). Jones’\ncomponents or characteristics of ‘moral intensity’ include:\nconsequences (i.e., magnitude of consequences, probability\nof effect, temporal immediacy, and concentration of effect);\nsocial consensus that a proposed act is evil or good; and the\nproximity or ‘the feeling of nearness’ (social, cultural, psy-\nchological, or physical) the agent has to those affected. The\nmoral intensity of the issue is proposed by Jones to inﬂuence\neach of the four stages of EDM and can act as both an\nindependent and moderating variable.\nMost other rationalist models proposed since 1991\nappear to be a variation or a combination of Rest ( 1986)\nand Jones ( 1991).\n14 Sonenshein ( 2007) groups the\nrationalist approaches into what he considers to be three\n‘prominent streams of research’: (i) manager as philoso-\npher (e.g., Hunt and Vitell 1986); (b) person-situation\n(Trevin˜o 1986); and (iii) issue-contingent (Jones 1991).\nWhat unites all of these theoretical models however is the\nemphasis on the rational cognitive process used by decision\nmakers to resolve ethical dilemmas. While rationalist\napproaches tend to recognize that intuition or emotion\nmight play a role in EDM,\n15 they would never be deter-\nminative of one’s moral judgments. Rationalist approaches\nare now beginning to recognize their limitations however,\nincluding constraints such as ‘bounded rationality’ (or\nmore speciﬁcally ‘bounded ethicality,’\n16 see Chugh et al.\n2005), or due to other cognitive biases that affect how\ninformation is processed (Messick and Bazerman 1996;\nTrevin˜o et al. 2006).17\nNon-rationalist (Intuitionist/Sentimentalist)\nApproaches\nAnother stream of EDM research has developed that argues\nthat a non-rationalist approach involving intuition (a cog-\nnitive process) and/or emotion or sentiments (an affective\nprocess) should be considered more central or ‘sovereign’\nto the moral judgment process of EDM (Saltzstein and\nKasachkoff 2004, p. 274). For example, ‘‘ …recent work in\nmoral psychology shows that ethical decisions are fre-\nquently informed by one’s feelings and intuitions’’ (Ruedy\net al. 2013, p. 532).\nIn terms of intuition, this non-rationalist research stream\nposits that intuitive (i.e., gut sense) and emotive processes\n(i.e., gut feelings) tend to at least initially generate moral\njudgments. For example, according to Haidt ( 2001): ‘‘The\ncentral claim of the social intuitionist model is that moral\njudgment is caused by quick moral intuitions and is fol-\nlowed (when needed) by slow, ex post facto moral rea-\nsoning’’ (Haidt2001, p. 818). Haidt states ( 2001, p. 814):\nIntuitionism in philosophy refers to the view that there\nare moral truths and that when people grasp these\ntruths they do so not by a process or ratiocination and\nreﬂection but rather by a process more akin to per-\nception, in which one ‘just sees without argument that\nthey are and must be true’ …Intuitionist approaches in\nmoral psychology, by extension, say that moral intu-\nitions (including moral emotions) come ﬁrst and\ndirectly cause moral judgments …Moral intuition is a\nkind of cognition, but it is not a kind of reasoning.\n18\n14 For example, other rationalist models include the ‘general theory\nmodel’ proposed by Hunt and Vitell ( 1986), a ‘behavior model’\nproposed by Bommer et al. ( 1987), and a ‘reasoned action’ model\nproposed by Dubinsky and Loken ( 1989) based on the theory of\nreasoned action (Fishbein and Ajzen 1975). In conducting a summary\nof various early models, Brady and Hatch ( 1992) propose that at least\nfour of the models (Ferrell and Gresham 1985; Hunt and Vitell 1986;\nTrevin˜o 1986; Bommer et al. 1987) contain the same four elements\n(1) a decision process, modiﬁed by (2) internal and (3) external\nfactors, leading to (4) ethical or unethical behavior.\n15 For example, Rest himself refers to the cognitive–affective\ninteractions that take place during each of the four stages of EDM\n(Rest 1984, p. 27). According to Rest ( 1986, p. 6), the moral\nawareness stage involves trying to understand our own ‘gut feelings’\nand in terms of the moral judgment stage ‘‘ …most people seem to\nhave at least intuitions about what’s morally right or wrong’’ ( 1986,\np. 8). Rest states: ‘‘ …there are different affect and cognition\ninteractions in every component’’ ( 1984, p. 28). He also states:\n‘‘…I take the view that there are no moral cognitions completely\ndevoid of affect, no moral affects completely devoid of cognitions,\nand no moral behavior separable from the cognitions and affects that\nprompt the behavior’’ (Rest 1986, p. 4). Hunt and Vitell ( 1986, p. 10)\nalso refer to the ‘feeling of guilt’ one might experience if behavior\nand intentions are inconsistent with one’s ethical judgments.\n16 ‘Bounded ethicality’ can be deﬁned as one making decisions that\nrun counter to values or principles without being aware of it (Chugh\net al. 2005; Palazzo et al. 2012).\n17 In terms of cognitive biases, Messick and Bazerman ( 1996)\npropose a series of theories about the world, other people, and\nourselves which are suggested to help explain the often unethical\ndecisions that executives make. In terms of theories about the world,\npeople often ignore possible outcomes or consequences due to ﬁve\nbiases: ‘ ‘…ignoring low-probability events, limiting the search for\nstakeholders, ignoring the possibility that the public will ‘ﬁnd out,’\ndiscounting the future, and undervaluing collective outcomes’’ ( 1996,\np. 10).\n18 Moral reasoning might also be argued to potentially take place\nwithout a conscious, effortful deliberation, suggesting it can be\nclassiﬁed as a form of intuition. Intuition might also be classiﬁed as a\nvery basic form of moral reasoning, meaning there is no real dispute\nbetween the two forms of processing, but rather they merely represent\na difference in degree (i.e., time or effort) of processing. However,\nbecause moral reasoning involves non-automatic inferential process-\ning, moral reasoning can be distinguished from intuition not only in\nterms of degree but also in terms of the kind of processing taking\nplace (see Wright 2005, pp. 28–29 and 44–45).\nEthical Decision-Making Theory: An Integrated Approach 759\n123	paragraph	5	22027	28531	\N	0	1040	6504	62	en	\N	\N	\N	f	\N	\N	\N	\N	\N	2025-08-27 20:36:49.630258	2025-08-27 20:36:49.630259	\N	59
2315	In other words, ‘‘ …moral reasoning is retroactive: It\nseeks to rationalize previous judgments and not to arrive at\nthose judgments’’ (Saltzstein and Kasachkoff 2004,\np. 276). One way to express the intuitive process is by\nsaying: ‘‘I don’t know, I can’t explain it, I just know it’s\nwrong’’ (Haidt2001, p. 814).\nEmotion or sentiment, deﬁned as one’s ‘feeling state’\n(Gaudine and Thorne 2001, p. 176), has also become more\nexplicitly incorporated into EDM research: ‘‘ …[C]umula-\ntive evidence from empirical research supports the asser-\ntion that ethical decision making is based not only on\nintuitive but also on emotion-based mechanisms, and that\nemotions constitute a key component of moral decision\nmaking’’ (Salvador and Folger 2009, pp. 11–12). Tangney\net al. ( 2007, p. 346) also note the importance of emotion in\nrelation to EDM: ‘‘Moral emotions may be critically\nimportant in understanding people’s behavioral adherence\n(or lack of adherence) to their moral standards.’’ Emotions\nthat have been suggested as being more directly related to\nEDM can be categorized into: (i) ‘pro-social’ emotions\nwhich promote morally good behavior such as empathy,\nsympathy, concern, or compassion\n19; (ii) ‘self-blame’\nemotions such as guilt and shame; or (iii) or ‘other-blame’\nemotions, such as contempt, anger, and disgust (see Prinz\nand Nichols 2010).\n20\nSeveral researchers have attempted to explain how\nemotion impacts EDM. Haidt ( 2001) as a non-rationalist\nappears to directly link emotion to intuition with little\nemphasis placed on reason. According to Elfenbein ( 2007,\np. 348): ‘‘The three main perspectives on the relationship\nbetween emotion and cognition are that emotion interferes\nwith cognition, that emotion serves cognition, and that the\ntwo are intertwined …’’ Greene et al. ( 2001) link emotions\ndirectly to the cognitive process and state (p. 2107):\n‘‘…emotional responses generated by the moral-personal\ndilemmas have an inﬂuence on and are not merely inci-\ndental to moral judgment.’’\n21 According to Damasio\n(1994), emotion is not in conﬂict with reason but provides\ncrucial support to the reasoning process by acting as a\nregulator of conduct. Another similar means to explain the\nrelationship between emotion and reason is by describing\nemotions as the ‘hot system’ (‘go’), which can undermine\nefforts to self-control one’s behavior. In contrast, the ‘cool\nsystem’ (‘know’) which is cognitive, contemplative, and\nemotionally neutral can potentially control the ‘hot system’\nthrough what is referred to as ‘moral willpower’ (Metcalfe\nand Mischel 1999).\n22\nThe non-rationalist approaches have been persuasively\nargued by researchers such as Haidt ( 2001) and Sonenshein\n(2007). Building on the works of philosophers like\nShaftesbury and Hume, Haidt ( 2001, p. 816) suggests that:\n‘‘…people have a built-in moral sense that creates plea-\nsurable feelings of approval toward benevolent acts and\ncorresponding feelings of disapproval toward evil and\nvice.’’ The relationship between emotions and intuition is\nnot so clear however. Monin et al. ( 2007, p. 101) state that:\n‘‘The difference between intuitions and emotions …seems\nto be that intuitions are behavioral guides or evaluations\nthat directly follow from an emotional experience.’’ Dane\nand Pratt ( 2007, pp. 38–39) refer to intuitive judgments as\n‘‘…affectively charged, given that such judgments often\ninvolve emotions’’ and are ‘‘…detached from rationality.’’\nKahneman ( 2003) states: ‘‘The operations of [intuition] are\ntypically fast, automatic, effortless, associative, implicit\n(not available to introspection), and often emotionally\ncharged.’’ This seems to suggest that emotions either affect\nor cause intuitions and are thus importantly related, or in\nother cases, emotions may directly affect any of the four\nEDM stages (Gaudine and Thorne 2001). It is important to\nnote however that not all intuitive judgments are neces-\nsarily emotionally charged, and that intuitions should be\nconsidered to be a cognitive (albeit non-deliberate) process\nevoked by the situation: ‘‘It must be stressed …that intu-\nition, reasoning, and the appraisals contained in emo-\ntions…are all forms of cognition’’ (Haidt 2001, p. 818).\nProposed Reformulation: Integrated Ethical\nDecision-Making (I-EDM) Model\nBuilding on previous EDM models and in order to address\nthe key divergence outlined above between the rationalist\nand non-rationalist approaches to EDM, a reformulated and\nmore integrative EDM model, referred to as ‘Integrated\nEthical Decision Making’ (or I-EDM), will now be\ndescribed (see Fig. 1 below).\nAt its most basic level, there are two major components\nto the I-EDM model: (1) the EDM process (including\n19 While positive emotions such as empathy are generally associated\nwith ethical behavior, it may also be the case that positive affect arises\nfollowing unethical behavior (e.g., cheating) which can then reinforce\nadditional future unethical behavior. See: Ruedy et al. ( 2013).\n20 The sorts of emotions that have been suggested as impacting EDM\ninclude anger; anxiety; compassion; distress; dominance; embarrass-\nment; empathy; fear; grief; guilt; hope; humiliation; love; meaning-\nlessness; mercy; pride; regret; remorse; responsibility; sadness;\nshame; and sympathy (see: Haidt 2001; Agnihotri et al. 2012).\nEisenberg ( 2000) provides a review of the research on guilt, shame,\nempathy, and moods in relation to morality.\n21 ‘Moral-personal’ dilemmas (as opposed to ‘impersonal’ dilemmas)\nthat trigger an emotional response relate to situations such as deciding\nwhether to physically push someone onto a trolley track to save the\nlives of many others. See Greene et al. ( 2001).\n22 Moral willpower (or self-sanction) can act like a ‘moral muscle’\nthat can be depleted following heavy use, or strengthened over time\n(see Muraven et al. 1999).\n760 M. S. Schwartz\n123	paragraph	6	28533	34384	\N	0	891	5851	51	en	\N	\N	\N	f	\N	\N	\N	\N	\N	2025-08-27 20:36:49.63026	2025-08-27 20:36:49.630261	\N	59
2316	antecedents and subsequents along with lack of moral\nawareness); and (2) the factors (or variables) that inﬂuence\nthe EDM process. The EDM process is composed of four\nbasic stages: (i) awareness; (ii) judgment; (iii) intention;\nand (iv) action/behavior, and in this respect continues to\nreﬂect the basic process framework proposed by Rest\n(1984, 1986). The antecedents to the EDM process include\nbasic environmental norms, while the subsequent stages of\nthe process include potential learning feedback loops . The\nEDM factors that inﬂuence the process fall into two basic\ncategories: (i) individual; and (ii) situational (Trevin˜o\n1986). The I-EDM model assumes that ethical behavior is\ncontingent on which particular individual is facing the\nethical dilemma (e.g., different individuals may act dif-\nferently when faced with the same dilemma), and (ii) the\nsituational context within which an individual faces a\ndilemma (e.g., the same individual can behave differently\ndepending on the particular situation one is facing or\nenvironment one is situated within). The following will\nﬁrst describe the individual and situational factors that can\ninﬂuence each of the stages of EDM, followed by a\ndescription of each stage in the Integrated-EDM process.\nIndividual Factors\nMost EDM models refer to individual factors or variables\nincluding, for example, ego strength, ﬁeld dependence, and\nlocus of control (Trevin ˜o 1986), values (Ferrell and Gre-\nsham 1985), or personal experiences (Hunt and Vitell\n1986). It may however be more useful to utilize a broader\nconstruct that captures all of the individual factors. Toward\nthis end, the I-EDM model attempts to collate together all\nthe individual factors into one general overarching main\nconstruct: one’s ‘moral capacity ’ (see Hannah et al. 2011).\nThere are two inter-related but distinct components that\ncomprise an individual’s moral capacity: (i) moral char-\nacter disposition ; and (ii) integrity capacity . Moral\ncapacity is deﬁned as the ability of an individual to avoid\nmoral temptations, engage in the proper resolution of eth-\nical dilemmas, and ultimately engage in ethical behavior.\nIn other words, one’s moral capacity is based not only on\none’s level of moral maturity and the core ethical values\nthey possess, but the extent to which they will cling to\nthose values even when faced with pressures to act other-\nwise. Each component of moral capacity will now be\ndescribed in more detail.\nThe ﬁrst component of an individual’s moral capacity is\none’smoral character disposition . A number of researchers\nhave raised the concern that this factor is lacking in EDM\nmodels. According to Pimental et al. ( 2010, p. 360): ‘‘The\npresently available models are insufﬁcient [because] they\nfail to ﬁnd that individuals’ characteristics are integral to\nthe identiﬁcation of ethical dilemmas.’’ Others suggest that\n‘‘…‘bad’ or ‘good’ apples, or bad features of otherwise\ngood apples play a role in decision making as well’’\n(Watson et al. 2009, p .12). Damon and Hart ( 1992, p. 455)\npropose that: ‘‘ …there are both theoretical and empirical\nreasons to believe that the centrality of morality to self may\nAwareness\n(Recognize)\nConsulta/g415on\n(Conﬁrm)\nIssue\nNorms\nLearning\n(Retrospect)\nEmo/g415on\n(Feel)\nRa/g415onaliza/g415on\n(Jus/g415fy)\nReason\n(Reﬂect)\nIntui/g415on\n(Sense)\nJudgment\n(Evaluate)\nInten/g415on\n(Commit)\nBehavior\n(Act)\nLackof\nAwareness\n(Overlook)\nSitua/g415on\n(Issue;Organiza/g415on;\nPersonal)\nIndividual\n(MoralCapacity)\nModera/g415ng\nFactors\nFig. 1 Integrated ethical decision-making model. Primary sources of\nthe model: Rest ( 1984, 1986) (four-component model); Jones ( 1991)\n(issue-contingency model); Trevin˜o( 1986) (person–situation interac-\ntionist model); Tenbrunsel and Smith-Crowe ( 2008) (lack of moral\nawareness); Hannah et al. ( 2011) (moral capacity); Haidt ( 2001)\n(social intuitionist model). Legend solid box—mental state; dotted\nbox—mental process; solid circle—active conduct; dotted circle—\nfactor/variable\nEthical Decision-Making Theory: An Integrated Approach 761\n123	paragraph	7	34386	38442	\N	0	601	4056	32	en	\N	\N	\N	f	\N	\N	\N	\N	\N	2025-08-27 20:36:49.630262	2025-08-27 20:36:49.630263	\N	59
2317	be the single most powerful determiner of concordance\nbetween moral judgment and conduct.’’ It is therefore clear\nthat moral character disposition should be incorporated into\nany EDM model.\nWhile there might be several different approaches to\ndeﬁning moral character disposition, 23 for the purposes of\nthe Integrated-EDM model, it is intended to be a broad\nconstruct that would potentially capture other moral char-\nacter concepts that have been identiﬁed in the EDM liter-\nature. These concepts include ‘cognitive stage of moral\ndevelopment’ (CMD) (Kohlberg 1973; Trevin˜o 1986),\n‘current ethical value system’\n24 (CEVS) (Jackson et al.\n2013), ‘personal value orientations’ (Weber 1993; Bartlett\n2003), ‘philosophy/value orientation’ (O’Fallon and But-\nterﬁeld 2005), ‘ethical ideology’ 25 (Schlenker 2008),\n‘ethical predisposition’ (Brady and Wheeler 1996; Rey-\nnolds 2006b26), and ‘moral sensitivity’ (Reynolds 2008).\nMoral character disposition is closely related to the con-\nstruct of ‘moral maturation’ described by Hannah et al.\n(2011, pp. 669–670) which includes moral ‘complexity’\n(i.e., ‘‘knowledge of concepts of morality’’), ‘meta-cogni-\ntive ability’ (i.e., the ‘engine’ used to ‘‘deeply process\ncomplex moral knowledge’’), and ‘moral identity’\n27 (i.e.,\n‘‘….individuals’ knowledge about themselves as moral\nactors’’). For the purposes of the I-EDM model, an indi-\nvidual’s moral character disposition is deﬁned as one’s\nlevel of moral maturity based on their ethical value system,\nstage of moral development, and sense of moral identity.\nMoral capacity however also includes another construct\nrelated not just to one’s moral character disposition but to\nthe commitment or motivation one has to act consistently\naccording to their moral character disposition through their\nability to self-regulate (see Jackson et al. 2013). The con-\nstruct that comes closest to capturing this consistency and\ntherefore what will be used in the I-EDM model is one’s\nintegrity capacity suggested by Petrick and Quinn ( 2000).\nThey deﬁne ‘integrity capacity’ as the individual’s\n‘‘…capability for repeated process alignment of moral\nawareness, deliberation, character and conduct …’’ (2000,\np. 4).\nThe construct of integrity capacity overlaps closely with\nRest’s ( 1986) conceptualization of ‘moral character’ or\nHannah et al.’s ( 2011) ‘moral conation’ construct (i.e., the\nimpetus or moral willpower to act in accordance with one’s\nethical values or principles). Integrity capacity would\ninclude concepts such as ‘moral ownership’ (i.e., the extent\nto which one feels responsible over the ethical nature of their\nown actions or the actions of others), ‘moral efﬁcacy’ (i.e.,\nbelieving one has the capability to act ethically), and ‘moral\ncourage’ (i.e., the strength and commitment to resist pres-\nsures to act unethically) (see Hannah et al. 2011). An indi-\nvidual’s moral capacity is continuously tested depending on\nthe circumstances one is facing. Whether one’s moral\ncharacter disposition will be maintained when put to the test\ndepends directly on one’s integrity capacity, meaning there\nis a direct relationship between the two constructs.\nAccording to the I-EDM model, rather than directly\naffecting awareness, judgment, intention, or behavior as\nsuggested in much EDM research, the key EDM individual\nvariables found in EDM literature potentially affect one’s\n‘moral capacity’ which then potentially affects the various\nEDM stages. These include demographic variables (e.g.,\nage, gender, education, nationality, work experience, etc.),\npersonality or psychological variables (e.g., cognitive\nmoral development/CMD, locus of control, ego strength,\netc.), and variables more directly related to one’s ethical\nexperience (e.g., religion/religiosity, ethics training, pro-\nfessional education, etc.).\n28 Figure 2 below depicts the\nindividual moral capacity construct.\nSituational Context\nAs indicated above, all dominant EDM models refer to\nsituational or organizational factors that can impact the\ndecision-making process (Bommer et al. 1987; Ferrell and\nGresham 1985; Hunt and Vitell 1986; Trevin˜o 1986).\nBuilding on these models along with Jones ( 1991), the\n23 For example, one might include intuition and emotions (or the\nability to control one’s emotions) as part and parcel of one’s moral\ncharacter based on a virtue-based ethics approach. For the purposes of\nthe I-EDM model, intuition and emotion are described as part of the\nmoral judgment stage; however, the extent and manner in which this\ntakes place would potentially depend on one’s moral character\ndisposition.\n24 ‘Current ethical value system’ (CEVS) is the framework that\nguides an individual’s ethical choices and behavior (see Jackson et al.\n2013, p. 236).\n25 Ethical ideology is ‘‘ …an integrated system of beliefs, values,\nstandards, and self-assessments that deﬁne an individual’s orientation\ntoward matters of right and wrong’’ (McFerran et al. 2010, p. 35).\nOne’s ‘ethical ideology’ is made up of one’s ‘moral personality’ and\n‘moral identity’ (McFerran et al. 2010). Schlenker ( 2008, p. 1079)\nsuggests that there is a continuum between a ‘principled ideology’\n(one believes moral principles exist and should guide conduct\n‘‘…regardless of personal consequences or self-serving rationaliza-\ntions’’) and ‘expedient ideology’ (one believes moral principles have\nﬂexibility and that deviations for personal gain are justiﬁable).\n26 Ethical predisposition is deﬁned as ‘‘ …the cognitive frameworks\nindividuals prefer to use in moral decision making’’ (Reynolds 2006b,\np. 234).\n27 ‘Moral identity’ has been suggested by several theorists as playing\nan important self-regulatory role in linking moral attitudes to one’s\nbehavior. See Schlenker ( 2008, p. 1081). See also Lapsley and\nNarvaez ( 2004) for a review of the concept of moral identity.\n28 See O’Fallon and Butterﬁeld ( 2005) and Craft ( 2013) for a\ncomplete list of EDM individual-related variables that would\npotentially fall into these categories.\n762 M. S. Schwartz\n123	paragraph	8	38444	44451	\N	0	888	6007	71	en	\N	\N	\N	f	\N	\N	\N	\N	\N	2025-08-27 20:36:49.630264	2025-08-27 20:36:49.630265	\N	59
2318	situational context of the I-EDM model comprises three\ncomponents: (1) the issue; (2) the organizational infras-\ntructure; and (3) personal factors.\nIssue\nWith respect to the ﬁrst component, rather than focusing on\nthe good or bad ‘apples’ (i.e., individual characteristics) or\nthe good or bad ‘barrels’ (i.e., organizational environment),\nsome have argued that the issue itself should be the focus of\nEDM (Jones 1991;W e b e r 1996; Bartlett 2003;K i s h -\nGephart et al. 2010). While Jones’ ( 1991) issue-contingent\nmodel clearly moved EDM in this direction, it is not clear if\nit was moved far enough in certain respects. For the pur-\nposes of the I-EDM model, the issue variable would consist\nof three dimensions: (i) issue moral intensity; (ii) issue\nimportance; and (iii) issue complexity. Each dimension of\nthe issue-related variable will now be described.\nAs indicated above, Jones ( 1991) suggests that the moral\nintensity of an issue can impact each of the four stages of the\nEDM process. One initial concern with Jones’ moral inten-\nsity construct is that the dimensions of moral intensity can\nsimply be incorporated into the moral judgment stage\n(Herndon 1996).\n29 Setting this concern aside, Jones’ char-\nacteristics of moral intensity can also be considered some-\nwhat limited in a normative sense. Jones only considers\nconsequences (either positive or negative), social norms, and\nthe proximity or ‘closeness’ the agent has to those affected,\nas tied to moral intensity. For the purposes of the I-EDM\nmodel, the moral intensity of an issue would include not only\nJones’ ( 1991) criteria, but would be extended to include\nadditional deontological (i.e., duty-based) and fairness\ndimensions (see May and Pauli 2002; McMahon and Harvey\n2007; Singer 1996). In other words, the moral intensity of an\nissue would be expected to increase if an individual is facing\na situation which might require breaking rules (e.g., codes),\nlaws, or promises, acting in a disloyal or dishonest manner,\ninfringing the moral rights of others, or relate to notions of\nretributive, compensatory, procedural, or distributive justice.\nAs indicated by some researchers, ‘ ‘ …other ethical per-\nspectives should also be considered …such as fairness or law\nbreaking where harm was not involved’ ’ as part of the moral\nintensity construct (Butterﬁeld et al. 2000, p. 1010). A higher\nlevel of moral intensity would then presumably increase the\nlikelihood of moral awareness (see May and Pauli 2002).\nIssue importance is another component that would be\ntaken into account by the I-EDM model. Issue importance is\ndeﬁned as the ‘‘ …perceived personal relevance or impor-\ntance of an ethical issue to an individual’’ (Robin et al. 1996,\np. 17, emphasis added). A number of researchers have shifted\nJones’ (1991) focus on the moral intensity of an issue to the\nsubjective importance placed on a particular issue by a par-\nticular individual. The reason for this approach is that any\nobjective determination of issue intensity would be irrele-\nvant unless the decision maker himself or herself subjec-\ntively perceived the issue as being of importance (Haines\net al. 2008; Valentine and Hollingworth 2012;Y u 2015;\nDedeke 2015). If issue importance to the decision maker is\nnot considered, the ethical implications of the issue might be\nignored altogether leading to a lack of moral awareness.\nAnother dimension of an issue that appears to have been\nignored in EDM theoretical models is the extent to which an\nissue is perceived to be very complex. Issue complexity is\ndeﬁned as issues that are perceived by the decision maker to\nbe hard to understand or difﬁcult to resolve. Warren and\nSmith-Crowe ( 2008, p. 90) refer to issue complexity in\nrelation to the type of moral judgment (reason versus intu-\nition) that might take place: ‘‘ …the intuitionists are not\nseeking judgments from individuals on issues that are new,\ncomplex, or have many options.’’ Issue complexity can\ninvolve the perceived degree of conﬂict among competing\nmoral standards or multiple stakeholder claims. Issues can\nalso be perceived as more complex when the decision maker\nhas never faced a similar situation before, or faces a wide\nrange of different alternatives. Issue complexity might also\ninclude other components such as the degree to which there\nare complicated facts involved or multiple factual assump-\ntions that need to be made due to a lack of relevant infor-\nmation being available. Such information may be necessary\nin order to properly understand the ramiﬁcations of a par-\nticular issue (e.g., potential future harm to oneself or others).\nIn a similar vein, relevant knowledge on the issue has been\nsuggested as being linked with ‘‘…one’s ability to engage in\neffortful cognitive activity’’ (see Street et al. 2001, p. 263).\nAs a result, regardless of its intensity or importance, the mere\nperceived complexity of the issue or dilemma could possibly\ncause one to ignore facing and addressing the issue alto-\ngether, leading to a type of ‘moral paralysis.’ For example,\ndeciding whether to blow the whistle on ﬁrm misconduct can\nbe a highly complex and difﬁcult decision with ramiﬁcations\nto multiple parties (De George 2010) which might prevent\nMoral Character \nDisposition Integrity Capacity \nIndividual Moral Capacity\nDemographics Ethical\nExperience\nPersonality/\nPsychological\nFig. 2 Individual moral capacity\n29 For example, Herndon states ( 1996, p. 504): ‘‘While Jones ( 1991)\nadds the concept of moral intensity which is the degree of ‘badness’\nof an act; it can be placed in the consequences and behavioral\nevaluation portions of the synthesis integrated model.’’\nEthical Decision-Making Theory: An Integrated Approach 763\n123	paragraph	9	44453	50155	\N	0	918	5702	50	en	\N	\N	\N	f	\N	\N	\N	\N	\N	2025-08-27 20:36:49.630266	2025-08-27 20:36:49.630267	\N	59
2319	coming to any judgment on the ethically appropriate action\nto take. Due to its potential impact on at least the moral\nawareness and moral judgment stages, perceived ‘issue\ncomplexity’ is also included in the I-EDM model as part of\nthe issue-related situational construct in addition to issue\nintensity and issue importance.\nOrganizational Environment\nThe second component of the situational context is the\norganizational environment. One potentially useful way to\ndenote organizational factors is to collectively refer to them\nas representing the ‘ethical infrastructure’ of the organi-\nzation (Tenbrunsel et al. 2003; Trevin˜o et al. 2006). Ethical\ninfrastructure, as the overarching construct for all organi-\nzational environmental variables, is deﬁned as ‘‘ …the\norganizational elements that contribute to an organization’s\nethical effectiveness’’ (Tenbrunsel et al. 2003, p. 286). The\nethical infrastructure would include formal and informal\nsystems such as communication systems (i.e., codes of\nconduct or ethics, missions, performance standards, and\ncompliance or ethics training programs), surveillance sys-\ntems (i.e., performance appraisal and reporting hotlines),\nand sanctioning systems (i.e., rewards and punishments\nincluding evaluations, promotions, salary, and bonuses).\n30\nBoth the formal and informal systems form part of ‘‘ …the\norganizational climates that support the infrastructure’’\n(Tenbrunsel et al. 2003, p. 286). A substantial body of\nempirical research has examined the potential impact the\nvarious components of ethical infrastructure can have on\nethical decision making by individuals within organiza-\ntions (see O’Fallon and Butterﬁeld 2005; Craft 2013). The\nunderlying assumption is that ﬁrms with a strong ethical\nculture and climate generally lead to more employees\nbecoming aware of ethical issues and the importance of\nbehaving in what would be considered by the company to\nbe in an ethical manner (Ethics Resource Center 2014).\nThe impact of signiﬁcant or ‘referent’ others/peers\nwhich can lead to one imitating or learning from the\nbehavior of others along with authority pressures (e.g.,\nmanagers or executives) would also be included in the\nI-EDM model as part of the ethical infrastructure (e.g.,\nHunt and Vitell 1986; Bommer et al. 1987; Trevin˜o 1986).\nOpportunity, or ‘‘ …the occurrence of circumstances to\npermit ethical/unethical behavior’’ would also be included\nas a component of an organization’s ethical infrastructure\nin terms of organizational culture (Ferrell et al. 1989,\np. 61).\nPersonal Situation\nOne’s personal situation, as distinct from one’s moral\ncapacity, is the ﬁnal component of the situational context.\nThe key variable of one’s personal situation is one’s per-\nceived ‘need for personal gain,’ which can result from\nliving beyond one’s means, high debt, ﬁnancial losses, or\nunexpected ﬁnancial needs (see Albrecht 2003). Another\nmeans of expressing one’s ‘need for personal gain’ at any\ngiven point in time is what might be referred to as one’s\ncurrent state of ‘ethical vulnerability.’\n31 This means that if\none is in a weak ﬁnancial position, facing signiﬁcant per-\nceived ﬁnancial pressures or obligations, with few or non-\nexistent career or job alternatives available, one would\npresumably be in a much weaker position to resist uneth-\nical requests and put one’s job, promotion, or bonus at risk\nor be willing to accept the ‘personal costs’ of taking moral\naction (Trevin˜o 1986). Other constraints such as time\npressure or limited ﬁnancial resources to do what one\nknows to be right can also be considered part of the per-\nsonal situational context (Trevin ˜o 1986).\nOne or more of the situational factors can come into\ndirect conﬂict with one’s moral character disposition, and\nwhether one is able to withstand the pressures one faces\nwould be dependent on the extent of one’s integrity\ncapacity. Figure 3 below depicts each of the components of\nthe situational context construct.\nProcess Stages of EDM\nNow that the individual and situational context factors have\nbeen described, the process stages of the I-EDM model\nwhich can be affected by the moderating variables can be\noutlined. In terms of the process of the I-EDM model, the\ninitial starting point are the norms (i.e., environment) that\nare prevalent which tend to determine whether an ethical\nissue or dilemma potentially exists. Norms are deﬁned as\nthose prevailing standards or expectations of behavior held\nby members of a particular group or community. Norms\ncan simultaneously exist at several different levels,\nincluding at the societal/cultural/national level (e.g., brib-\nery is seen as being generally acceptable), at the organi-\nzational level\n32 (e.g., dating a work colleague is considered\nunacceptable according to corporate policy), or at the work\ngroup level (e.g., padding expense accounts is viewed as\nacceptable by one’s work colleagues).\n30 As an alternative to ‘ethical infrastructure,’ others (e.g., Valentine\net al. 2013) have used the term ‘ethical context’ to refer to both the\n‘ethical culture’ (Trevin˜o et al. 1998) and the ‘ethical climate’ of the\norganization (Victor and Cullen 1988).\n31 The notion of ‘vulnerability’ has apparently received little\nattention in the business ethics literature. See: Brown ( 2013).\n32 The ﬁrm’s ethical infrastructure should be considered distinct from\norganizational-level norms, although there would clearly be a\nrelationship between them. This discussion is however beyond the\nscope of the paper.\n764 M. S. Schwartz\n123	paragraph	10	50157	55673	\N	0	840	5516	61	en	\N	\N	\N	f	\N	\N	\N	\N	\N	2025-08-27 20:36:49.630268	2025-08-27 20:36:49.630269	\N	59
2320	Several EDM models propose that there is an ‘environ-\nmental’ context within which the existence of an ethical\nissue or dilemma can arise (Ferrell and Gresham 1985; Hunt\nand Vitell 1986; Jones 1991; Brass et al. 1998; Randall\n1989; Trevin˜o 1986). While the sources of these norms\nmight also be discussed, such as deeply embedded socio-\nlogical, political, legal, or religious considerations or views,\nthis discussion is beyond the scope for the purposes of this\npaper. For the I-EDM model, a potential ethical issue or\ndilemma arises when there is a situation whereby different\nnorms apply, each of which cannot be followed at the same\ntime. This basic starting point of the EDM process has also\nbeen referred to as the ‘eliciting situation’ (Haidt 2001).\nMoral Awareness\nAssuming that a situation with a potential ethical issue or\ndilemma exists due to conﬂicting norms, the next question\nis whether the individual becomes aware of the existence of\nthe issue or dilemma. Moral awareness is deﬁned as the\npoint in time when an individual realizes that they are\nfaced with a situation requiring a decision or action that\ncould the affect the interests, welfare, or expectations of\noneself or others in a manner that may conﬂict with one or\nmore moral standards (Butterﬁeld et al. 2000). Moral\nawareness that a particular situation raises ethical issues\ncan take place simply due to an individual’s moral capacity\nand inherent ability to recognize ethical issues (Hannah\net al. 2011) and/or as a result of a ﬁrm’s ethical infras-\ntructure (i.e., including codes, training, meetings, or other\ndisseminated ethical policy communications) (Tenbrunsel\net al. 2003). If one becomes aware that an ethical issue or\ndilemma exists, then one has by deﬁnition identiﬁed at\nleast two different possible courses of action, and can then\npotentially engage in an EDM process consisting of the\nmoral judgment and intention stages.\n33 The following will\nnow explain how the ‘lack of moral awareness’ process\ntakes place, considered to be an equally important com-\nponent of the I-EDM model.\nLack of Moral Awareness\nThe vast majority of EDM theoretical models, by relying\non Rest ( 1986), presume that only through moral awareness\nof the potential ethical nature of a dilemma can one ulti-\nmately engage in ethical behavior. For example, Sonen-\nshein states ( 2007, p. 1026): ‘‘ …moral awareness is often\nviewed as binary—you either recognize the ethical issue or\nyou fail to do so …Consequently, research has tended to\nfocus on whether moral awareness is present or absent as a\nprecondition for activating the other stages of rationalist\nmodels (Jones 1991,p .3 8 3 ) …’’ What appears to be lack-\ning in current EDM models however is the depiction of\none’s lack of moral awareness, meaning one does not\nrealize (i.e., they overlook) that the situation one is expe-\nriencing raises ethical considerations.\nThere are now several overlapping theories that have\nbeen proposed in EDM literature to help explain the pro-\ncesses or reasons by which one might lack moral aware-\nness, also referred to as unintentional ‘amoral awareness’\n(Tenbrunsel and Smith-Crowe 2008) or unintentional\n‘amoral management’ (Carroll 1987).\n34 For example,\nBandura’s theoretical work on moral disengagement is an\nimportant theoretical source underlying one’s lack of moral\nawareness. According to Bandura ( 1999), moral disen-\ngagement involves a process by which one convinces\noneself in a particular context that ethical standards do not\napply. Moral standards regulate behavior only when self-\nregulatory mechanisms or ‘moral self-sanctions’ (i.e., one’s\nconscience) are activated. Psychological processes that can\nprevent this activation include ‘‘ …restructuring of inhu-\nmane conduct into a benign or worthy one by moral jus-\ntiﬁcation, sanitizing language, and advantageous\ncomparison; disavowal of a sense of personal agency by\ndiffusion or displacement of responsibility; disregarding or\nminimizing the injurious effects of one’s actions; and\nIssue Organization (Ethical \nInfrastructure)\nSituational Context\nPersonal\nIntensity;\nImportance;\nComplexity\nPerceived Need \nfor Gain;\nConstraints\n(time, financial \nability)\nCommunication; \nTraining; \nSanctioning \nSystems\n(including\npeers, authority,\nopportunity, \nrewards, sanctions)\nFig. 3 Situational context for EDM\n33 There is however a risk of moral awareness being confounded with\nmoral judgment, especially when the deﬁnition of moral awareness\nFootnote 33 continued\nincludes consideration of one or more ethical standards (see Reynolds\n2006b, p. 233).\n34 Carroll ( 1987) refers to ‘amoral managers,’ who can either act\nintentionally or unintentionally. Unintentional amoral managers\n‘‘…do not think about business activity in ethical terms. These\nmanagers are simply casual about, careless about, or inattentive to the\nfact that their decisions and actions may have negative or deleterious\neffects on others. These managers lack ethical perception and moral\nawareness; that is, they blithely go through their organizational lives\nnot thinking that what they are doing has an ethical dimension to it.\nThey may be well intentioned but are either too insensitive or\negocentric to consider the impacts on others of their behavior’’\n(Carroll 1987, p. 11).\nEthical Decision-Making Theory: An Integrated Approach 765\n123	paragraph	11	55675	61006	\N	0	823	5331	37	en	\N	\N	\N	f	\N	\N	\N	\N	\N	2025-08-27 20:36:49.63027	2025-08-27 20:36:49.630271	\N	59
2321	attribution of blame to, and dehumanization of, those who\nare victimized’’ (Bandura 1999, p. 193).\nSimilar to moral disengagement, one can also lack moral\nawareness due to ethical fading . Ethical fading is ‘‘ …the\nprocess by which the moral colors of an ethical decision\nfade into bleached hues that are void of moral implica-\ntions’’ (Tenbrunsel and Messick 2004, p. 224). In order for\n‘ethical fading’ to take place, people engage in self-de-\nception through the use of euphemistic language (e.g.,\n‘aggressive’ accounting practices; ‘right sizing’) and other\ntechniques to ‘shield themselves’ from their own unethical\nbehavior. Another similar concept used to explain one’s\nlack of moral awareness is ethical blindness ,o r‘ ‘ …the\ndecision maker’s temporary inability to see the ethical\ndimension of a decision at stake’’ (Palazzo et al. 2012,\np. 324). Ethical blindness includes three aspects: (i) people\ndeviate from their own values and principles; (ii) this\ndeviation is temporary in nature; and (iii) the process is\nunconscious in nature (Palazzo et al. 2012, p. 325).\n35\nAnother theory related to a lack of moral awareness is\nthe use of non-moral decision frames , which occurs when\none focuses on the business or legal implications of issues\nrather than on the ethical considerations (Tenbrunsel and\nSmith-Crowe 2008; Dedeke 2015). The process of framing\nin a non-moral manner leading to a lack of awareness can\nresult due to insufﬁcient or biased information gathering, or\nsocially constructing the facts in a particular manner (So-\nnenshein 2007). Moral myopia can also take place which is\nsimilarly deﬁned as ‘‘ ….a distortion of moral vision that\nprevents moral issues from coming into focus’’ (Drum-\nwright and Murphy 2004, p. 7). These initial theories or\nprocesses (moral disengagement, ethical fading, ethical\nblindness, non-moral decision frames, and moral myopia)\nappear to relate more directly to one’s work environment\nleading to a lack of moral awareness. In other words, if one\nis situated in a work environment which tends to ignore\nethical considerations in its decision making or consistently\nprioritizes the bottom line over ethical concerns, as well as\nuses non-moral language in its operations,\n36 then one\nwould likely be less inclined to be morally aware when\nfacing a dilemma.\nMoral awareness however could be attributable to the\nparticular individual’s inherent nature, and thus directly\nrelated to one’s moral character disposition described\nabove. For example, moral awareness can result from\nmoral attentiveness , which has been deﬁned as: ‘‘ …the\nextent to which an individual chronically perceives and\nconsiders morality and moral elements in his or her expe-\nriences’’ (Reynolds2008, p. 1027). Similar to the notion of\nmoral attentiveness, others have linked moral awareness to\nthe concept of mindfulness, which is described as ‘‘ …an\nindividual’s awareness both internally (awareness of their\nown thoughts) and externally (awareness of what is hap-\npening in their environment)’’ (Ruedy and Schweitzer\n2010, p. 73). It may be that a lack of mindfulness exac-\nerbates one’s self-serving cognition, self-deception, and\nunconscious biases leading to unethical behavior: ‘‘Mindful\nindividuals may feel less compelled to ignore, explain\naway, or rationalize ideas that might be potentially\nthreatening to the self, such as a conﬂict of interest or a\npotential bias’’ (Ruedy and Schweitzer 2010, p. 76).\nEngaging in moral imagination (Werhane 1998) might\nalso potentially lead to moral awareness, while failing to\nengage in moral imagination might lead to a lack of moral\nawareness. Moral imagination involves whether one has\n‘‘…a sense of the variety of possibilities and moral con-\nsequences of their decisions, the ability to imagine a set of\npossible issues, consequences, and solutions’’ (Werhane\n1998, p. 76). When one is only able to see one option rather\nthan create imaginative solutions, one may be unaware that\none is even facing an ethical dilemma with a potentially\nmore ethical alternative being available. Figure 4 below\nsummarizes the theories or processes discussed above that\nhelp explain and contribute to moral awareness or a lack of\nmoral awareness.\nBy not including the phenomenon of ‘lack of moral\nawareness’ in EDM models, an important stream of EDM\nresearch is being ignored. Even if one is not aware that an\nethical dilemma exists, one can still engage in what might\nbe considered ‘unintentional’ ethical or unethical behavior\n(Tenbrunsel and Smith-Crowe 2008; Jackson et al. 2013).\nDue to the importance of understanding why there might be\na lack of moral awareness and the processes leading to it,\nwhich would presumably increase the potential for\nEthical \nIssue\n• Moral Disengagement\n Ethical Fading\n Ethical Blindness\n Non-Moral Framing\n Moral Myopia\n Moral Attentiveness\n Moral Mindfulness\n Moral Imagination\n Moral Framing \nMoral\nAwareness\nLack of Moral \nAwareness\nFig. 4 Processes affecting moral awareness\n35 The classic example of ‘ethical blindness’ comes from the recall\ncoordinator of the defective Ford Pinto vehicle who asked himself:\n‘‘Why didn’t I see the gravity of the problem and its ethical\novertones?’’ (Gioia1992, p. 383).\n36 This can also take place due to moral muting , which involves\nmanagers who ‘ ‘ …avoid moral expressions in their communica-\ntions…’’ (Bird and Waters 1989, p. 75).\n766 M. S. Schwartz\n123	paragraph	12	61008	66412	\N	0	856	5404	44	en	\N	\N	\N	f	\N	\N	\N	\N	\N	2025-08-27 20:36:49.630272	2025-08-27 20:36:49.630273	\N	59
2322	unethical behavior, the lack of moral awareness path is\ndepicted in the I-EDM model.\nMoral Judgment and Intention Stages of I-EDM\nThe moral judgment and intention stages represent the crux\nof the I-EDM model, and might be referred to as the actual\nEDM process that takes place. Moral judgment is deﬁned\nfor the purposes of the model as the determination of the\nmost ethically appropriate course of action among the\nalternatives. Moral intention is deﬁned as the commitment\nor motivation to act according to one’s moral values.\n37 This\nis the point in the I-EDM model where several different\nprocesses either affect moral judgment directly, or poten-\ntially interact with each other leading to judgment and\nintention. These mental processes include (i) emotion; (ii)\nintuition; (iii) reason; (iv) rationalization; as well as (v) the\nactive process of consultation.\nAs can be seen in Fig. 1 above, the Integrated-EDM\nmodel does not suggest that only reason or intuition is\ninvolved in the moral judgment process, but that both are\npotentially involved, along with emotion and rationaliza-\ntion. As indicated above, a growing number of researchers\nare indicating the importance of including what has been\nreferred to as the ‘dual process’ of both reason and emo-\ntion/intuition in any EDM model (e.g., see Elm and Radin\n2012; Marquardt and Hoeger 2009). For example, Woice-\nshyn ( 2011, p. 313) states [emphasis added]: ‘‘Following\nthe developments in cognitive neuroscience and neu-\nroethics (Salvador and Folger 2009) and paralleling the\ngeneral decision-making literature (Dane and Pratt 2007),\nmost researchers have since come to hold a so-called dual\nprocessing model of ethical decision making.’’\nDespite this fact, very few studies provide a clear visual\ndepiction of the inﬂuence of reason, intuition, and emotion\non EDM. Haidt ( 2001) includes reason (or reasoning) as\nwell as intuition in his schematic social intuitionist model,\nalthough as indicated above reason serves primarily a post\nhoc rationalization function and emotion (or affect) appears\nto be comingled with intuition. Reynolds ( 2006a) proposes\na two-system model which also includes both intuition (the\nreﬂexive X-system) and reason (the higher order conscious\nreasoning C-system) but appears to have left out the impact\nof emotion. Woiceshyn ( 2011) also attempts to integrate\nreason and intuition through a process she calls ‘integration\nby essentials’ and ‘spiraling’ but does not explicitly include\nemotion. Gaudine and Thorne ( 2001) visually depict the\ninﬂuence of emotion on the four EDM stages but do not\nrefer to intuition. Other ﬁelds, such as social psychology,\nhave attempted to merge intuition and reason together\nschematically (Strack and Deutsch 2004).\nOne EDM study was identiﬁed however that shows the\nlinks between reason, intuition, and emotion. Dedeke\n(2015) does so by proposing a ‘cognitive-intuitionist’\nmodel of moral decision making. In the model, intuitions\nare referred to as reﬂexive ‘automatic cognitions,’ which\nmay or may not interact with ‘automatic emotions.’ This\ninteraction is considered part of the ‘pre-processing’ pro-\ncess which often takes place and is then ‘‘ …subject to\nreview and update by the moral reﬂection/reasoning pro-\ncess’’ (Dedeke2015, p. 446). Emotion can also ‘sabotage’\nthe moral reﬂection stage for some people and thus an\n‘emotional control variable’ is proposed ‘‘…that enables an\nindividual to …modify…their feelings stages’’ (Dedeke\n2015, p. 448). Dedeke’s ‘cognitive-intuitionist’ model\nrecognizes and captures the importance of moving future\nEDM theory in a more integrative manner, in other words,\none that incorporates reason, intuition, and emotion into the\nEDM process.\nWhile the actual degree of inﬂuence of reason versus\nintuition/emotion and the sequencing or nature of the\ninteraction remain open for debate and further research\n(Dane and Pratt 2007), virtually everyone now agrees that\nboth approaches play a role in EDM.\n38 The relationships\nbetween emotion and intuition upon each other, as well as\non moral judgment and intention, should therefore be\nindicated in any revised EDM model. As indicated by\nHaidt ( 2001, p. 828):\nThe debate between rationalism and intuitionism is an\nold one, but the divide between the two approaches\nmay not be unbridgeable. Both sides agree that people\nhave emotions and intuitions, engage in reasoning,\nand are inﬂuenced by each other. The challenge, then,\nis to specify how these processes ﬁt together.\nRationalist models do this by focusing on reasoning\nand then discussing the other processes in terms of\ntheir effects on reasoning. Emotions matter because\nthey can be inputs to reasoning …The social intu-\nitionist model proposes a very different arrangement,\n37 Ethical intention is sometimes linked with ethical behavior as\nbeing part of the ‘same phenomenon’ (Reynolds 2006a, p. 741) or\nthey can be combined together as representing one’s ‘ethical choice’\n(Kish-Gephart et al. 2010, p. 2). It may be therefore that ‘intention’\nshould be eliminated from Rest’s ( 1986) four-stage model, but might\ncontinue to act as a proxy for measuring judgment or behavior in\nEDM empirical research (see Mencl and May 2009, p. 205). For the\npurposes of the I-EDM model, intention remains theoretically distinct\nfrom behavior.\n38 Some have argued that the debate over reason versus intuition/\nemotion is actually based on whether one is experiencing a moral\ndilemma requiring a reasoning process, versus an affective or\nemotion-laden process based on reacting to a shocking situation such\nas considering the prospect of eating one’s own dog (Monin et al.,\n2007, p. 99).\nEthical Decision-Making Theory: An Integrated Approach 767\n123	paragraph	13	66414	72118	\N	0	891	5704	45	en	\N	\N	\N	f	\N	\N	\N	\N	\N	2025-08-27 20:36:49.630274	2025-08-27 20:36:49.630275	\N	59
2323	one that fully integrates reasoning, emotion, intuition,\nand social inﬂuence.\nYet despite the claim of ‘fully’ integrating reason,\nemotion, and intuition, Haidt ( 2001) clearly makes reason\nplay a secondary role to intuition in a potential two-stage\nprocess, highlighting its lack of importance to EDM (see:\nSaltzstein and Kasachkoff 2004). As opposed to the EDM\nprocess models discussed above, the following will brieﬂy\nexplain how the I-EDM model incorporates emotion,\nintuition, reason, and rationalization along with their\npotential inter-relationships as part of a neuro-cognitive-\naffective process as depicted in Fig. 1 above.\nEmotion\nEmotion is considered an important part of the moral\njudgment and intention stages in the I-EDM model. In\nmany cases, emotion might be the ﬁrst response when\nfaced with an ethical situation or dilemma (Haidt et al.\n1993). Emotions such as empathy can lead to intuitive\njudgments (e.g., ‘affect-laden intuitions’), often referred to\nas ‘gut feelings’ about the rightness or wrongness of certain\nactions (Tofﬂer 1986). For example, the discovery that a\nwork colleague is downloading child pornography, or that\none’s ﬁrm is selling defective and dangerous goods to\nunknowing consumers, may trigger an emotional response\nsuch as a feeling of anger or disgust. This may then lead to\nan intuitive moral judgment that such behavior is unac-\nceptable and needs to be addressed. In addition to affecting\nintuitions, emotion may impact or affect the moral rea-\nsoning process (Damasio 1994; Metcalfe and Mischel\n1999; Dedeke 2015). Emotions can also lead to moral\nrationalization, for example, envy of one’s work colleagues\nwho are paid more than oneself for the same performance\nmay lead one to morally rationalize padding expense\naccounts. Emotions may impact other stages of the EDM\nprocess in addition to judgment such as intention by cre-\nating a motivation to act (see Eisenberg 2000; Huebner\net al. 2009).\nIntuition\nThe I-EDM model presumes that for most dilemmas,\nincluding those that are non-complex or involve moral\ntemptations (right versus wrong), an intuitive cognitive\nprocess takes place at least initially after being evoked by\nthe situation (Haidt 2001; Reynolds 2006a; Dedeke 2015),\nand in this respect, intuition plays a signiﬁcant role in the\nEDM process. Intuition is the more automatic and less\ndeliberative process often leading to an initial intuitive\njudgment that may or may not be acted upon. For example,\nseveral situations may provide an automatic gut ‘sense’ of\nrightness and wrongness, such as paying a bribe or over-\ncharging a customer. The moral reasoning or the moral\nrationalization process is then expected typically to follow\none’s initial intuitive judgment.\nReason\nThe I-EDM model considers the moral reasoning process\nto be just as important as intuition (Saltzstein and\nKasachkoff 2004), and not limited to merely post hoc\nrationalization (e.g., Haidt 2001). For example, in deciding\nwhether to dismiss an underperforming colleague who is\nalso considered a close friend, a more deliberative moral\nreasoning process may take place, leading to a particular\nmoral judgment. Moral reasoning provides the means by\nwhich the decision maker can reﬂect upon and resolve if\nnecessary any conﬂict among the moral standards (e.g.,\nconsequences versus duties versus fairness) or competing\nstakeholder claims. More complex ethical dilemmas would\npresumably lead to a more challenging moral reasoning\nprocess, the proper resolution of which may require a\nstronger individual moral capacity. Moral intention is then\nexpected to follow one’s moral judgment depending on\none’s integrity capacity and situational context.\nMoral Rationalization\nThis is the point during the I-EDM process when moral\nrationalization, which has not been made explicit in any of\nthe dominant EDM models, becomes important. Moral\nrationalization has over time become recognized as a more\nimportant psychological process with respect to EDM.\nMoral rationalization has been deﬁned as ‘‘ …the cognitive\nprocess that individuals use to convince themselves that\ntheir behavior does not violate their moral standards’’\n(Tsang\n2002, p. 26) and can be used to justify both small\nunethical acts as well as serious atrocities (Tsang 2002,\np. 25). Another way of thinking about rationalization is\nthrough the process of belief harmonization which involves\n‘‘…a process of arranging and revising one’s needs, beliefs,\nand personal preferences into a cohesive cognitive network\nthat mitigates against cognitive dissonance’’ (Jackson et al.\n2013, p. 238). Rest seems to suggest that the rationalization\nprocess is a type of faulty or ‘ﬂawed’ moral reasoning\n(1986, p. 18):\n…a person may distort the feelings of obligation by\ndenying the need to act, denying personal responsi-\nbility, or reappraising the situation so as to make\nalternative actions more appropriate. In other words,\nas subjects recognize the implications of [their moral\njudgment and intention] and the personal costs of\nmoral action become clear, they may defensively\n768 M. S. Schwartz\n123	paragraph	14	72120	77198	\N	0	781	5078	42	en	\N	\N	\N	f	\N	\N	\N	\N	\N	2025-08-27 20:36:49.630276	2025-08-27 20:36:49.630278	\N	59
2324	reappraise and alter their interpretation of the situa-\ntion [i.e., the awareness stage] so that they can feel\nhonorable, but at less cost to themselves.\nThere are several potential theories underlying moral\nrationalization. Moral rationalization may be based on the\nnotion of moral appropriation or ‘‘…the desire for moral\napproval from oneself or others’’ (Jones and Ryan 1997,\np. 664). The moral rationalization process has also been\ntied to what Ariely ( 2012, p. 53) refers to as fudge factor\ntheory, which helps explain how many are prepared to\ncheat a little bit through ‘ﬂexible’ moral reasoning while\nstill maintaining their sense of moral identity. Similarly,\nmoral balance theory permits one to engage in moral\ndeviations as long as one’s moral identity remains ‘satis-\nfactory’ (Nisan 1995).\nAnand et al. ( 2005) extend Bandura ( 1999) and Sykes\nand Matza ( 1957) by outlining the means by which one can\nrationalize corrupt or unethical acts.\n39 These methods\ninclude (Anand et al. 2005, p. 11): (i) denial of responsi-\nbility (‘My arm was being twisted’); (ii) denial of injury\n(‘No one was really harmed’); (iii) denial of victim (‘They\ndeserved it’); (iv) social weighting (‘Others are worse than\nwe are’); (v) appeal to higher authorities (‘We answered to\na higher cause’); and (vi) balancing the ledger (‘I deserve\nit’). In terms of the timing of rationalization in the EDM\nprocess, according to Anand et al. ( 2005, p. 11): ‘‘Ra-\ntionalizations can be invoked prospectively (before the act)\nto forestall guilt and resistance or retrospectively (after the\nact) to ease misgivings about one’s behavior. Once\ninvoked, the rationalizations not only facilitate future\nwrongdoing but dull awareness that the act is in fact\nwrong.’’\nIf one’s moral judgment based on moral reasoning is\ncontrary to one’s self-perceived moral identity, typically\ndue to a preference or desire to act toward fulﬁlling one’s\nself-interest, then one may engage in a biased or distorted\nprocess of moral rationalization. By doing so, one is able to\navoid experiencing the emotions of guilt, shame, or\nembarrassment. Some refer to this state as being one of\n‘moral hypocrisy’ or the appearance of being moral to\nthemselves or others while ‘‘…avoiding the cost of actually\nbeing moral’’ (Batson et al. 1999, p. 525). While moral\nrationalization is a cognitive (albeit possibly subconscious)\nprocess, it may also affect, be affected by, or work in\nconjunction with (i.e., overlap) the moral reasoning process\n(Tsang 2002), intuition (Haidt 2001), or emotion (Bandura\n1999). With few exceptions, moral rationalization is often\nunfortunately ignored or simply assumed to exist by most\nEDM models,\n40 but due to its importance is included in the\nI-EDM model.\nMoral Consultation\nOne additional potential process that can impact one’s\njudgment, intention, or behavior is that of moral consul-\ntation. Moral consultation is deﬁned as the active process\nof reviewing ethics-related documentation (e.g., codes of\nethics) or discussing to any extent one’s ethical situation\nor dilemma with others in order to receive guidance or\nfeedback. While it is clear that not all individuals will\nengage with others in helping to determine the appropri-\nate course of action, any degree of discussion with col-\nleagues, managers, family members, friends, or ethics\nofﬁcers, or the review of ethics documentation when\nfacing an ethical dilemma, would constitute moral\nconsultation.\nMoral consultation as a procedural step of EDM, while\nnot incorporated into the dominant EDM models, is referred\nto by some EDM theorists (see Sonenshein 2007; Hamilton\nand Knouse 2011). For example, Haidt ( 2001, 2007) refers\nto individuals being inﬂuenced or persuaded through their\nsocial interactions with others in his ‘social intuitionist’\nmodel and suggests that ‘‘ …most moral change happens as\na result of social interaction’’ (Haidt 2007, p. 999). Moral\nconsultation should be considered particularly important in\nan organizational setting given that ﬁrms often encourage\nand provide opportunities to their employees to discuss and\nseek ethical guidance from others or from ethics docu-\nmentation (Weaver et al. 1999; Stevens 2008). While moral\nconsultation is generally expected to improve ethical deci-\nsion making, the opposite might also occur. One may dis-\ncover through discussion that ‘unethical’ behavior is\nconsidered acceptable to others or even expected by one’s\nsuperiors potentially increasing the likelihood of acting in\nan unethical manner.\nEthical Behavior\nOne’s moral judgment ( evaluation), whether based on\nemotion ( feel), intuition ( sense), moral reasoning ( reﬂect),\nmoral rationalization ( justify), and/or moral consultation\n(conﬁrm), may then lead to moral intention ( commitment),\nwhich may then lead to ethical or unethical behavior ( ac-\ntion) (see Fig. 1 above). Each of the above processes (i.e.,\nemotion, intuition, reason, rationalization, and\n39 Heath ( 2008) provides a similar list of moral rationalizations\nwhich he refers to as ‘neutralization techniques.’\n40 Three notable exceptions include Reynolds ( 2006a), who makes\nrationalization explicit in his model as a retrospective (e.g., post hoc\nanalysis) process operating as part of the higher order conscious\nreasoning system, while the decision-making model proposed by\nTsang ( 2002) positions moral rationalization (along with situational\nfactors) as being central to the ethical decision-making process.\nDedeke ( 2015) also indicates that rationalization of one’s reﬂexive\n(intuitive or emotion-based) judgment can be part of the ‘moral\nreﬂection’ stage of EDM where moral reasoning also takes place.\nEthical Decision-Making Theory: An Integrated Approach 769\n123	paragraph	15	77200	82913	\N	0	884	5713	49	en	\N	\N	\N	f	\N	\N	\N	\N	\N	2025-08-27 20:36:49.630279	2025-08-27 20:36:49.630279	\N	59
2325	consultation) can impact moral judgment either directly or\nfollowing interaction with each other. The behavior can\neither relate to ‘proscriptive’ (e.g., avoid harm) or ‘pre-\nscriptive’ (e.g., do good) actions (see Janoff-Bulman et al.\n2009) and can be of different degrees of ethicality in terms\nof the ‘rightness’ or ‘wrongness’ of the behavior (see\nHenderson 1984; Green 1994; and Kaler 2000).\nFeedback Loops\nPotential feedback loops represent the ﬁnal procedural\nstep in the I-EDM model. Behavior may be followed by\nperceived positive or negative consequences to others or\nto oneself through rewards or punishments/sanctions for\nthe decision made or actions taken. When the conse-\nquences are observed by the decision maker, learning\ninvolving internal retrospection over one’s actions can\ntake place, which may then affect one’s individual moral\ncapacity and thereby the decision-making process the next\ntime an ethical dilemma arises. According to Reynolds\n(2006a, p. 742): ‘‘ …anyone who has lain awake at night\ncontemplating the experiences of the previous day knows\nthat retrospection is a key component of the ethical\nexperience…’’ The learning might be either positive or\nnegative, for example, one might determine that acting in\nan unethical manner was worth the risks taken, or that\nacting ethically was not worth the personal costs suffered.\nIn either case, such realizations might impact future\ndecision making. Similar feedback loops including con-\nsequences and learning are included in several (but not\nall) EDM models. For example, Ferrell and Gresham\n(1985) refer to ‘evaluation of behavior,’ while Hunt and\nVitell ( 1986, p. 10) refer to ‘actual consequences’ which\nis the ‘‘major learning construct in the model’’ which\nfeeds back to one’s ‘personal experiences.’ Stead et al.\n(1990) refer to their feedback loop as one’s ‘ethical\ndecision history.’\nOne additional feedback loop of the I-EDM model (see\nFig. 1) ﬂows from behavior to awareness, in that only after\none acts (e.g., telling a white lie, fudging an account) one\nmay realize that there were ethical implications that ought\nto have been considered (i.e., if there was originally a lack\nof awareness) meaning that the matter ought to have been\nconsidered differently. The original issue or dilemma may\nthen potentially be judged again based on any of the pro-\ncesses (i.e., emotion, intuition, reason, rationalization, and/\nor consultation) leading to a different judgment and addi-\ntional behavior (e.g., admission, apology, steps to ﬁx the\nmistake, etc.). To provide greater clarity, Table 1 below\nsummarizes the various moderating factors, while Table 2\nbelow summarizes the process stages of the I-EDM model\nincluding the potential interaction between emotion, intu-\nition, reason, rationalization, and consultation.\nBasic Propositions\nIn general, according to the I-EDM model, ethical behavior\nis assumed to be more likely to take place when there is\nstrong individual moral capacity (strong moral character\ndisposition and integrity capacity), strong issue character-\nistics (high level of moral intensity and perceived impor-\ntance with a lack of complexity), strong ethical\ninfrastructure (including weak perceived opportunity with\nstrong sanctions for unethical behavior), along with weak\npersonal constraints (weak perceived need for personal\ngain, sufﬁcient time and ﬁnancial resources). Unethical\nbehavior tends to take place when there is weak individual\nmoral capacity (weak moral character disposition and\nintegrity capacity), weak issue characteristics (weak issue\nintensity and importance along with a high level of issue\ncomplexity), weak ethical infrastructure (including strong\nperceived opportunities, weak sanctions, along with strong\nauthority pressures and peer inﬂuence to engage in uneth-\nical behavior), and a lack of personal constraints (strong\nperceived need for personal gain and time pressures).\nTeaching, Research, and Managerial Implications\nThe I-EDM model has a number of important potential\nimplications for both the academic and business commu-\nnities. In terms of teaching implications, despite the history\nof major corporate scandals, a debate continues over the\nutility of business ethics education (Bosco et al. 2010). For\nthose who teach business ethics, many still argue over what\nthe proper teaching objectives should consist of (Sims and\nFelton 2006). The I-EDM model suggests that the focus of\nbusiness ethics education should be on two particular\nstages of EDM, the moral awareness stage, and the moral\njudgment stage. In terms of moral awareness, by presenting\nan array of relevant ethical dilemmas, and then sensitizing\nstudents to the potential ethical implications arising from\nthe dilemmas, might increase students’ general level of\nmoral awareness following the course.\nBy explaining the tools of moral reasoning, including\nconsequentialism and deontology, students may be better\nprepared and able to engage in moral reasoning. The\ndangers of pure egoism in the form of greed along with the\ndeﬁciencies of relativism as a moral standard need to be\npointed out. Students should also be exposed to the moral\nrationalization process, so that they will be more aware\nwhen it is taking place and can better guard against its\noccurrence. New approaches such as ‘giving voice to val-\nues’ (Gentile 2010) can also help provide a better means\nfor students and others to transition their values from\nintentions to actual behavior rather than merely focus on\nthe moral reasoning process. Ultimately, business students\n770 M. S. Schwartz\n123	paragraph	16	82915	88479	\N	0	847	5564	46	en	\N	\N	\N	f	\N	\N	\N	\N	\N	2025-08-27 20:36:49.63028	2025-08-27 20:36:49.630281	\N	59
2326	need to possess the tools to be able to determine and\nactualize what might be considered ethical versus unethical\nbehavior.\nResearch that focuses on the relationship and interaction\nbetween emotion, intuition, reasoning, rationalization, and\nmoral consultation should be further pursued. It is not clear,\nfor example, the extent to which intuition and emotions\nimprove ethical decision making or hinder it. More research\non the particular aspects and types of ethical issues, beyond\nissue intensity such as issue importance and complexity,\nshould be examined to see which process (i.e., emotion,\nintuition, reason, consultation) is utilized to a greater\ndegree, and to what extent this leads to more ethical\nbehavior with fewer instances of rationalization. New sci-\nentiﬁc methods and studies of brain activity should assist in\nthis endeavor. Given that the current EDM models have\nonly partially explained the causes and processes of ethical\nbehavior, clearly more work needs to be done to revise\nEDM theory leading to more fruitful empirical examination.\nFuture EDM research should also continue to consider\nwhether certain individual and/or situational variables play\na more signiﬁcant causal or moderating role depending on\nwhich stage of EDM is taking place. For example, it may\nbe that during the awareness and judgment stages, one’s\nmoral character disposition, issue intensity, issue impor-\ntance, and issue complexity are more important, while\nduring the intention to behavior stage, integrity capacity\nand perceived ‘need for gain’ might play more important\nroles. The role of biases and heuristics should also continue\nto be examined in relation to EDM during each of the\nstages.\nIn terms of managerial implications, the I-EDM model\nsuggests that ethical infrastructure and moral consultation\neach play an important role in EDM, with formal elements\nsuch as codes and training potentially being more impor-\ntant for awareness and judgment. The model also suggests\nthat hiring practices based on seeking individuals with\nstrong moral capacities should continue to be pursued,\nespecially for managers or senior executives. For managers\nand employees, the I-EDM model may have possible\nnormative implications as well, such as avoiding the sole\nuse of intuition and emotion whenever possible, taking\nsteps to improve one’s ethical awareness potential, and to\nalways be cognizant of rationalizations and biases affecting\nthe moral reasoning process.\nLimitations\nThe proposed I-EDM model contains a number of impor-\ntant limitations. In terms of scope, the I-EDM model is\nfocused on individual decision making and behavior, rather\nthan organizational, and is designed to apply mainly to the\nbusiness context. One could argue that the model is overly\nrationalist in nature by continuing to rely on Rest ( 1986)a s\nthe dominant framework to explain the EDM process, and\nTable 1 I-EDM moderating factors\nConcept/construct Deﬁnition and relationships Key sources\nIndividual moral\ncapacity\nThe ability to avoid moral temptations, engage in the proper resolution of ethical\ndilemmas, and engage in ethical behavior. Consists of one’s moral character\ndisposition and integrity capacity. Can impact each EDM stage\nHannah et al. ( 2011)\nMoral character\ndisposition\nAn individual’s level of moral maturity based on their ethical value system, stage of\nmoral development, and sense of moral identity. Primarily impacts the moral\nawareness and moral judgment stages\nKohlberg ( 1973);\nJackson et al. ( 2013)\nIntegrity capacity The capability to consistently act in a manner consistent with one’s moral character\ndisposition. Impacts primarily the intention and behavior stages\nPetrick and Quinn ( 2000)\nEthical issue A situation requiring a freely made choice to be made among alternatives that can\npositively or negatively impact others. Can impact each EDM stage\nJones ( 1991)\nIssue intensity The degree to which consequences, social norms, proximity, or deontological/fairness\nconsiderations affect the moral imperative in a situation. Can impact each EDM stage\nButterﬁeld et al. ( 2000)\nIssue importance The perceived personal relevance of an ethical issue by an individual. Direct\nrelationship with issue intensity. Primarily impacts the moral awareness stage\nRobin et al. ( 1996)\nIssue complexity The perceived degree of difﬁculty in understanding an issue. Based on perceived\nconﬂict among moral standards or stakeholder claims or required factual information\nor assumptions needed to be made. Primarily impacts the moral awareness and moral\njudgment stages\nStreet et al. ( 2001); Warren\nand Smith-Crowe ( 2008)\nOrganization’s ethical\ninfrastructure\nThe organizational elements that contribute to an organization’s ethical effectiveness.\nCan impact each EDM stage\nTenbrunsel et al. ( 2003)\nPersonal context The individual’s current situation which can lead to ‘ethical vulnerability’ including\n‘personal need for gain’ or time/ﬁnancial constraints. Can impact each EDM stage\nAlbrecht ( 2003)\nEthical Decision-Making Theory: An Integrated Approach 771\n123	paragraph	17	88481	93535	\N	0	759	5054	35	en	\N	\N	\N	f	\N	\N	\N	\N	\N	2025-08-27 20:36:49.630282	2025-08-27 20:36:49.630284	\N	59
2327	thus does not represent a purely synthesized model. The\nmanner and extent to which the variables and processes\nwere depicted by the I-EDM model as portrayed in Fig. 1\ncan be criticized as being too all encompassing and thus\nlacking sufﬁcient focus. It might on the other hand be\ncriticized as failing to take into account other key variables\nor processes involved in EDM that have been suggested in\nthe literature. For example, the role of inter-personal pro-\ncesses (rather than intra-personal processes) may not be\nsufﬁciently accounted for in the I-EDM model (Moore and\nGino 2013) despite recognizing the inﬂuence of peers/ref-\nerent others, authority pressures, the rationalization process\n(‘everyone is doing it’), and the consultation process.\nFinally, each element of the I-EDM model, including the\nindividual and situational context variables as well as the\nrelationship between and overlap among the variables and\neach of the process stages of EDM, requires further\ndetailed exploration and explication which hopefully fur-\nther research will address.\nConclusion\nThis paper attempts to address several deﬁciencies that\nappear to exist in current EDM theoretical models. It does\nso by merging together the key processes, factors, and\ntheories together, including emotion, intuition, moral rea-\nsoning, moral rationalization, and moral consultation along\nwith the key individual and situational variables. The\nproposed integrated model might be considered to take a\n‘person-situation’ interactionist approach along with an\n‘intuition/sentimentalist-rationalist’ approach to moral\njudgment. It attempts to clarify the key factors inﬂuencing\nEDM, and introduces or makes more explicit other factors\nsuch as ‘moral capacity’ including ‘moral character dis-\nposition’ and ‘integrity capacity,’ and additional situational\ncharacteristics of the issue beyond merely intensity\nincluding ‘issue importance’ and ‘issue complexity.’ As\nresearch suggests: ‘‘…most all of us may commit unethical\nbehaviors, given the right circumstances’’ (De Cremer et al.\nTable 2 I-EDM process stages and constructs\nProcess stages Deﬁnition and relationship with other I-EDM constructs and stages\nMoral awareness The point in time when an individual realizes that they are faced with a situation requiring a decision or action that could\naffect the interests, welfare, or expectations of oneself or others in a manner that may conﬂict with one or more moral\nstandards (Butterﬁeld et al. 2000)\nLack of moral\nawareness\nThe state of not realizing that a dilemma has moral implications. Leads to unintentional ethical or unethical behavior\n(Tenbrunsel and Smith-Crowe 2008)\nMoral judgment Determination of the ethically appropriate course of action among alternatives. Activates the moral intention stage (Rest\n1986)\nEmotion One’s feeling state. Can impact judgment directly (Greene et al. 2001). Can also impact the moral reasoning process\n(Damasio 1994; Greene et al. 2001; Huebner et al. 2009); trigger intuitions (Haidt 2001), or can lead to rationalization\n(e.g., through feelings of guilt or sympathy for others) (Tsang 2002)\nIntuition A cognitive process involving an automatic and reﬂexive reaction leading to an initial moral judgment. Can lead to moral\njudgment directly (Haidt 2001). Can also impact emotion (Dedeke 2015), moral reasoning when there are unclear or\nconﬂicting intuitions (Haidt 2001), or lead to a rationalization process if judgment is contrary to one’s moral identity\n(Reynolds 2006a; Sonenshein 2007)\nReason The conscious and deliberate application of moral standards to a situation. Can impact moral judgment directly\n(Kohlberg 1973). Reason (‘cool system’) can also control emotions (‘hot system’) (Metcalfe and Mischel 1999).\nReason through ‘private reﬂection’ can lead to a new intuition (Haidt 2001), or can be ‘recruited’ to provide post hoc\nrationalizations (Dedeke 2015)\nMoral rationalization The conscious or unconscious process of explaining or justifying one’s intended or actual behavior in an ethically\nacceptable manner to oneself or others. Can lead to moral judgment directly (Tsang 2002). Can also impact emotion by\nforestalling or reducing guilt (Anand et al. 2005; Bandura 1999; Ariely 2012), lead to new intuitions (Haidt 2001), or\nover-ride moral reasoning through a biased or distorted cognitive process (Tsang 2002)\nMoral consultation Discussing to any extent one’s ethical dilemma with others or the review of ethical documentation (e.g., codes). Can be\noverridden by rationalization. Takes place after initial awareness, but could also take place after behavior.\nMoral intention The commitment or motivation to act according to one’s moral values. Affects moral behavior and can lead to moral\nconsultation (Rest 1986)\nEthical behavior Ethical behavior supported by one or more moral standards. Can be intentional (moral awareness) or unintentional (lack\nof moral awareness). Typically follows moral judgment and/or moral intention (Rest 1986)\nLearning The process of understanding and internalizing the impacts of one’s decisions. Can impact one’s moral capacity for\nfuture decisions (Reynolds 2006a)\n772 M. S. Schwartz\n123	paragraph	18	93537	98691	\N	0	761	5154	41	en	\N	\N	\N	f	\N	\N	\N	\N	\N	2025-08-27 20:36:49.630285	2025-08-27 20:36:49.630285	\N	59
2328	2010, p. 2). The possibility of a lack of moral awareness is\nalso depicted in the model, as well as ‘moral consultation’\nand the key feedback loops (i.e., learning and reassessment\nof behavior). Obviously, the proposed I-EDM model\nremains subject to further criticism, leading to the need to\nbe further modiﬁed as new EDM research is generated.\nThere are several other potential important deﬁciencies\nin the current state of EDM theory which are beyond the\nscope of this study that should be addressed as well. But if\na new proposed theoretical EDM model can at least\nproperly take into account the primary concerns raised\nabove, a potentially more robust model will have been\ndeveloped for use by a broader range of empirical\nresearchers. Given the extent of theoretical and empirical\nresearch that has now taken place, EDM in organizations\nmight be considered to be moving toward developing into a\n‘stand-alone’ academic ﬁeld (Tenbrunsel and Smith-Crowe\n2008, p. 545). Whether this eventually takes place is pri-\nmarily dependent on the strength of the theoretical EDM\nmodels being developed and tested by empirical EDM\nresearchers.\nReferences\nAgle, B. R., Hart, D. W., Thompson, J. A., & Hendricks, H. M. (Eds.).\n(2014). Research companion to ethical behavior in organiza-\ntions: Constructs and measures . Cheltenham, UK: Edward\nElgar.\nAgnihotri, J., Rapp, A., Kothandaraman, P., & Singh, R. K. (2012).\nAn emotion-based model of salesperson ethical behaviors.\nJournal of Business Ethics, 109 (2), 243–257.\nAlbrecht, W. S. (2003). Fraud examination . Thomson: Mason, OH.\nAnand, V., Ashforth, B. E., & Joshi, M. (2005). Business as usual:\nThe acceptance and perpetuation of corruption in organizations.\nAcademy of Management Executive, 19 (4), 9–23.\nAriely, D. (2012). The (honest) truth about dishonesty . New York:\nHarperCollins.\nAssociation of Certiﬁed Fraud Examiners. 2014. Report to the nations\non occupational fraud and abuse: 2014 Global Fraud Study ,\nAustin, Texas. http://www.acfe.com/rttn/docs/2014-report-to-\nnations.pdf.\nBandura, A. (1999). Moral disengagement in the perpetration of\ninhumanities. Personality and Social Psychology Review, 3 (3),\n193–209.\nBartlett, D. (2003). Management and business ethics: A critique and\nintegration of ethical decision-making models. British Journal of\nManagement, 14 , 223–235.\nBatson, D., Thompson, E. R., Seuferling, G., Whitney, H., &\nStrongman, J. A. (1999). Moral hypocrisy: appearing moral to\noneself without being so. Journal of Personality and Social\nPsychology, 77 (3), 525–537.\nBird, F. B., & Waters, G. A. (1989). The moral muteness of managers.\nCalifornia Management Review, 32 , 73–78.\nBommer, M., Gratto, C., Gravender, J., & Tuttle, M. (1987). A\nbehavioral model of ethical and unethical decision making.\nJournal of Business Ethics, 6 , 265–280.\nBosco, S. M., Melchar, D. E., Beauvais, L. L., & Desplaces, D. E.\n(2010). Teaching business ethics: The effectiveness of common\npedagogical practices in developing students’ moral judgment\ncompetence. Ethics and Education, 5 (3), 263–280.\nBrady, F. N., & Hatch, M. J. (1992). General causal models in\nbusiness ethics: An essay on colliding research traditions.\nJournal of Business Ethics, 11 , 307–315.\nBrady, F. N., & Wheeler, G. E. (1996). An empirical study of ethical\npredispositions. Journal of Business Ethics, 15 , 927–940.\nBrass, D. J., Butterﬁeld, K. D., & Skaggs, B. C. (1998). Relationships\nand unethical behavior: A social network perspective. Academy\nof Management Review, 23 (1), 14–31.\nBrown, E. (2013). Vulnerability and the basis of business ethics:\nFrom ﬁduciary duties to professionalism. Journal of Business\nEthics, 113 (3), 489–504.\nButterﬁeld, K. D., Trevin ˜o, L. K., & Weaver, G. R. (2000). Moral\nawareness in business organizations: Inﬂuences of issue-related\nand social context factors. Human Relations, 53 (7), 981–1018.\nCarroll, A. B. (1987). In search of the moral manager. Business\nHorizons, 30 (2), 7–15.\nCasali, G. L. (2011). Developing a multidimensional scale for ethical\ndecision making. Journal of Business Ethics, 104 , 485–497.\nChugh, D., Bazerman, M. H., & Banaji, M. R. (2005). Bounded\nethicality as a psychological barrier to recognizing conﬂicts of\ninterest. In D. Moore, G. Loewenstein, D. Cain, & M.\nH. Bazerman (Eds.), Conﬂicts of interest (pp. 74–95). New\nYork: Cambridge University Press.\nCraft, J. L. (2013). A review of the empirical ethical decision-making\nliterature: 2004–2011. Journal of Business Ethics, 117 , 221–259.\nDamasio, A. (1994). Descartes’ error: Emotion, reason, and the\nhuman brain . New York: Putnam.\nDamon, W., & Hart, D. (1992). Self-understanding and its role in\nsocial and moral development. In M. Bornstein & M. E. Lamb\n(Eds.), Developmental psychology: An advanced textbook (3rd\ned., pp. 421–464). Hillsdale, NJ: Erlbaum.\nDane, E., & Pratt, M. G. (2007). Exploring intuition and its role in\nmanagerial decision making. Academy of Management Review,\n32(1), 33–54.\nDe Cremer, D., Mayer, D. M., & Schminke, M. (2010). Guest editors’\nintroduction on understanding ethical behavior and decision\nmaking: A behavioral ethics approach. Business Ethics Quar-\nterly, 20 (1), 1–6.\nDe George, R. T. (2010). Business ethics (7th ed.). New York:\nPrentice Hall.\nDedeke, A. (2015). A cognitive-intuitionist model of moral judgment.\nJournal of Business Ethics, 126 , 437–457.\nDonaldson, T., & Dunfee, T. W. (1999). Ties that bind: A social\ncontracts approach to business ethics . Cambridge, MA: Harvard\nBusiness School Press.\nDrumwright, M. E., & Murphy, P. E. (2004). How advertising\npractitioners view ethics: Moral muteness, moral myopia, and\nmoral imagination. Journal of Advertising, 33 (2), 7–24.\nDubinsky, A. J., & Loken, B. (1989). Analyzing ethical decision\nmaking in marketing. Journal of Business Research, 19 , 83–107.\nEisenberg, N. (2000). Emotion, regulation, and moral development.\nAnnual Review of Psychology, 51 , 665–697.\nElfenbein, H. A. (2007). Emotion in organizations. The Academy of\nManagement Annals, 1 (1), 315–386.\nElm, D. R., & Radin, T. J. (2012). Ethical decision making: Special or\nno different? Journal of Business Ethics, 107 (3), 313–329.\nEthics Resource Center (2014). 2013 National business ethics survey.\nArlington, VA.\nFerrell, O. C., & Gresham, L. G. (1985). A contingency framework\nfor understanding ethical decision making in marketing. Journal\nof Marketing, 49 (3), 87–96.\nFerrell, O. C., Gresham, L. G., & Fraedrich, J. (1989). A synthesis of\nethical decision models for marketing. Journal of Macromar-\nketing, 9 (2), 55–64.\nEthical Decision-Making Theory: An Integrated Approach 773\n123	paragraph	19	98693	105291	\N	0	1009	6598	257	en	\N	\N	\N	f	\N	\N	\N	\N	\N	2025-08-27 20:36:49.630286	2025-08-27 20:36:49.630287	\N	59
2329	Fishbein, M., & Ajzen, I. (1975). Belief, attitude, intention, and\nbehavior: An introduction to theory and research . Reading, MA:\nAddison-Wesley.\nFord, R. C., & Richardson, W. D. (1994). Ethical decision making: A\nreview of the empirical literature. Journal of Business Ethics, 13 ,\n205–221.\nGaudine, A., & Thorne, L. (2001). Emotion and ethical decision-making\nin organizations. Journal of Business Ethics, 31 (2), 175–187.\nGentile, M. C. (2010). Giving voice to values: How to speak your\nmind when you know what’s right . New Haven, CT: Yale\nUniversity Press.\nGioia, D. (1992). Pinto ﬁres and personal ethics: A script analysis of\nmissed opportunities.Journal of Business Ethics, 11(5/6), 379–389.\nGreen, R. M. (1994). The ethical manager . New York: Macmillan\nCollege Publishing.\nGreene, J. D., Sommerville, R. B., Nystrom, L. E., Darley, J. M., &\nCohen, J. (2001). An fMRI investigation of emotional engage-\nment in moral judgement. Science, 293 , 2105–2108.\nHaidt, J. (2001). The emotional dog and its rational tail: A social\nintuitionist approach to moral judgment. Psychological Review,\n4, 814–834.\nHaidt, J. (2007). The new synthesis in moral psychology. Science,\n316, 998–1002.\nHaidt, J., Koller, S., & Dias, M. (1993). Affect, culture, and morality,\nor is it wrong to eat your dog? Journal of Personality and Social\nPsychology, 65 , 613–628.\nHaines, R., Street, M. D., & Haines, D. (2008). The inﬂuence of\nperceived importance of an ethical issue on moral judgment,\nmoral obligation, and moral intent. Journal of Business Ethics,\n81, 387–399.\nHamilton, J. B., & Knouse, S. B. (2011). The experience-focused model\nof ethical action. In S. W. Gilliland, D. D. Steiner, & D. P. Skarlicki\n(Eds.), Emerging perspectives on organizational justice and ethics\n(pp. 223–257). Charlotte, NC: Information Age Publishing.\nHannah, S. T., Avolio, B. J., & May, D. R. (2011). Moral maturation\nand moral conation: A capacity approach to explaining moral\nthought and action. Academy of Management Review, 36 (4),\n663–685.\nHeath, J. (2008). Business ethics and moral motivation: A crimino-\nlogical perspective. Journal of Business Ethics, 83 , 595–614.\nHenderson, V. E. (1984). The spectrum of ethicality. Journal of\nBusiness Ethics, 3 (2), 163–171.\nHerndon, N. C, Jr. (1996). A new context for ethics education\nobjectives in a college of business: Ethical decision-making\nmodels. Journal of Business Ethics, 15 (5), 501–510.\nHuebner, B., Dwyer, S., & Hauser, M. (2009). The role of emotion in\nmoral psychology. Trends in Cognitive Sciences, 13 (1), 1–6.\nHunt, S. D., & Vitell, S. (1986). A general theory of marketing ethics.\nJournal of Macromarketing, 6 (1), 5–16.\nJackson, R. W., Wood, C. M., & Zboja, J. J. (2013). The dissolution\nof ethical decision-making in organizations: A comprehensive\nreview and model. Journal of Business Ethics, 116 , 233–250.\nJanoff-Bulman, R., Sheikh, S., & Hepp, S. (2009). Proscriptive versus\nprescriptive morality: Two faces of moral regulation. Journal of\nPersonality and Social Psychology, 96 (3), 521–537.\nJones, T. M. (1991). Ethical decision making by individuals in\norganizations: An issue contingent model. The Academy of\nManagement Review, 16 (2), 366–395.\nJones, T. M., & Ryan, L. V. (1997). The link between ethical\njudgment and action in organizations: A moral approbation\napproach. Organization Science, 8 (6), 663–680.\nKahneman, D. (2003). A perspective on judgment and choice.\nAmerican Psychologist, 58\n, 697–720.\nKaler, J. (2000). Reasons to be ethical: Self-interest and ethical\nbusiness. Journal of Business Ethics, 27 (1/2), 161–173.\nKidder, R. M. (1995). How good people make tough choices:\nResolving the dilemmas of ethical living . New York: Simon &\nSchuster.\nKish-Gephart, J. J., Harrison, D. A., & Trevin ˜o, L. K. (2010). Bad\napples, bad cases, and bad barrels: Meta-analytic evidence about\nsources of unethical decisions at work. Journal of Applied\nPsychology, 95 (1), 1–31.\nKohlberg, L. (1973). The claim to moral adequacy of a highest stage\nof moral judgment. The Journal of Philosophy, 70 (18), 630–646.\nLapsley, D. K., & Narvaez, D. (2004). Moral development, self, and\nidentity. Mahwah, NJ: Lawrence Erlbaum Associates.\nLehnert, K., Park, Y., & Singh, N. (2015). Research note and review\nof the empirical ethical decision-making literature: Boundary\nconditions and extensions. Journal of Business Ethics , 129,\n195–219.\nLiedka, J. M. (1989). Value congruence: The interplay of individual\nand organizational value systems. Journal of Business Ethics,\n8(10), 805–815.\nLoe, T. W., Ferrell, L., & Mansﬁeld, P. (2000). A review of empirical\nstudies assessing ethical decision making in business. Journal of\nBusiness Ethics, 25 (3), 185–204.\nMarquardt, N., & Hoeger, R. (2009). The effect of implicit moral\nattitudes on managerial decision-making: An implicit social\ncognition approach. Journal of Business Ethics, 85 , 157–171.\nMay, D. R., & Pauli, K. P. (2002). The role of moral intensity in\nethical decision making. Business and Society, 41 (1), 84–117.\nMcFerran, B., Aquino, K., & Duffy, M. (2010). How personality and\nmoral identity relate to individuals’ ethical ideology. Business\nEthics Quarterly, 20 (1), 35–56.\nMcMahon, J. M. and Harvey, R. J. (2007). The effect of moral\nintensity on ethical judgment. Journal of Business Ethics , 72,\n335–357.\nMencl, J., & May, D. R. (2009). The effects of proximity and empathy\non ethical decision-making: An exploratory investigation. Jour-\nnal of Business Ethics, 85 , 201–226.\nMessick, D. M., & Bazerman, M. H. (1996). Ethical leadership and\nthe psychology of decision making. Sloan Management Review,\n37(2), 9–22.\nMetcalfe, J., & Mischel, W. (1999). A hot/cool system analysis of\ndelay of gratiﬁcation: Dynamics of willpower. Psychological\nReview, 106 , 3–19.\nMonin, B., Pizarro, D. A., & Beer, J. S. (2007). Deciding versus\nreacting: Conceptions of moral judgment and the reason-affect\ndebate. Review of General Psychology, 11 (2), 99–111.\nMoore, G., & Gino, F. (2013). Ethically adrift: How others pull our\nmoral compass from true North, and how we can ﬁx it. Research\nin Organizational Behavior, 33 , 53–77.\nMudrack, P. E., & Mason, E. S. (2013). Dilemmas, conspiracies, and\nSophie’s choice: Vignette themes and ethical judgments. Journal\nof Business Ethics, 118 , 639–653.\nMuraven, M., Baumeister, R. F., & Tice, D. M. (1999). Longitudinal\nimprovement of self-regulation through practice: Building self-\ncontrol strength through repeated exercise. Journal of Social\nPsychology, 139 , 446–457.\nNisan, M. (1995). Moral balance model. In W. M. Kurtines & J.\nL. Gewirtz (Eds.), Moral development: An introduction (pp.\n475–492). Boston: Allyn & Bacon.\nO’Fallon, M. J., & Butterﬁeld, K. D. (2005). A review of the\nempirical ethical decision-making literature: 1996–2003. Jour-\nnal of Business Ethics, 59 , 375–413.\nPalazzo, G., Krings, F., & Hoffrage, U. (2012). Ethical blindness.\nJournal of Business Ethics, 109 , 323–338.\nPan, Y., & Sparks, J. R. (2012). Predictors, consequence, and\nmeasurement of ethical judgments: Review and meta analysis.\nJournal of Business Research, 65 , 84–91.\n774 M. S. Schwartz\n123	paragraph	20	105293	112405	\N	0	1105	7112	295	en	\N	\N	\N	f	\N	\N	\N	\N	\N	2025-08-27 20:36:49.630288	2025-08-27 20:36:49.630289	\N	59
2330	Petrick, J. A., & Quinn, J. F. (2000). The integrity capacity construct\nand moral progress in business. Journal of Business Ethics, 23 ,\n3–18.\nPimental, J. R. C., Kuntz, J. R., & Elenkov, D. S. (2010). Ethical\ndecision-making: An integrative model for business practice.\nEuropean Business Review, 22 (4), 359–376.\nPrinz, J. J., & Nichols, S. (2010). Moral emotions. In J. M. Doris, &\nThe Moral Psychology Research Group (Eds.), The moral\npsychology handbook (pp. 111–146). Oxford: Oxford University\nPress.\nRandall, D. M. (1989). Taking stock: Can the theory of reasoned\naction explain unethical conduct? Journal of Business Ethics,\n8(11), 873–882.\nRandall, D. M., & Gibson, A. M. (1990). Methodology in business\nethics research: A review and critical assessment. Journal of\nBusiness Ethics, 9 , 457–471.\nRest, J. R. (1984). The major components of morality. In W.\nM. Kurtines & J. L. Gewirtz (Eds.), Morality, moral behavior,\nand moral development (pp. 24–38). New York: Wiley.\nRest, J. R. (1986). Moral development: Advances in research and\ntheory. New York: Praeger.\nRest, J., Narvaez, D., Bebeau, M. J., & Shoma, S. J. (1999).\nPostconventional thinking: A new-Kohlbergian approach . Mah-\nwah, New Jersey: Lawrence Erlbaum Associates.\nReynolds, S. J. (2006a). A neurocognitive model of the ethical\ndecision-making process: Implications for study and practice.\nJournal of Applied Psychology, 91 (4), 737–748.\nReynolds, S. J. (2006b). Moral awareness and ethical predispositions:\nInvestigating the role of individual differences in the recognition\nof moral issues. Journal of Applied Psychology, 91 (1), 233–243.\nReynolds, S. J. (2008). Moral attentiveness: Who pays attention to the\nmoral aspects of life? Journal of Applied Psychology, 93 (5),\n1027–1041.\nRobin, D. P., Reidenbach, R. E., & Forrest, P. J. (1996). The\nperceived importance of an ethical issue as an inﬂuence on the\nethical decision-making of ad managers. Journal of Business\nResearch, 35 , 17–28.\nRossouw, D., & Stu ¨ ckelberger, C. (Eds.) (2012). Global survey of\nbusiness ethics: In training, teaching and research . http://www.\nglobethics.net/documents/4289936/13403236/GlobalSeries_5_\nGlobalSurveyBusinessEthics_text.pdf.\nRuedy, N. E., Moore, C., Gino, F., & Schweitzer, M. E. (2013). The\ncheater’s high: The unexpected affective beneﬁts of unethical\nbehavior. Journal of Personality and Social Psychology, 105 (4),\n531–548.\nRuedy, N. E., & Schweitzer, M. E. (2010). In the moment: The effect\nof mindfulness on ethical decision making. Journal of Business\nEthics, 95 , 73–87.\nSaltzstein, H. D., & Kasachkoff, T. (2004). Haidt’s moral intuitionist\ntheory: A psychological and philosophical critique. Review of\nGeneral Psychology, 8 (4), 273–282.\nSalvador, R., & Folger, R. G. (2009). Business ethics and the brain.\nBusiness Ethics Quarterly, 19 (1), 1–31.\nSchlenker, B. R. (2008). Integrity and character: Implications of\nprincipled and expedient ethical ideologies. Journal of Social\nand Clinical Psychology, 27 (10), 1078–1125.\nSchminke, M. (1998). Managerial ethics: Moral management of\npeople and processes . Mahwah, NJ: Lawrence Erlbaum and\nAssociates.\nSchwartz, M. S. (2005). Universal moral values for corporate codes of\nethics. Journal of Business Ethics, 59 (1), 27–44.\nSchwartz, M. S., & Carroll, A. (2003). Corporate social responsibil-\nity: A three domain approach. Business Ethics Quarterly, 13\n(4),\n503–530.\nSinger, M. S. (1996). The role of moral intensity and fairness\nperception in judgments of ethicality: A comparison of\nmanagerial professionals and the general public. Journal of\nBusiness Ethics , 15, 469–474.\nSims, R. R., & Felton, E. L. (2006). Designing and delivering\nbusiness ethics teaching and learning. Journal of Business\nEthics, 63 , 297–312.\nSonenshein, S. (2007). The role of construction, intuition, and\njustiﬁcation in responding to ethical issues at work: The\nsensemaking-intuition model. Academy of Management Review,\n32(4), 1022–1040.\nStead, W. E., Worrell, D. L., & Stead, J. G. (1990). An integrative model\nfor understanding and managing ethical behavior in business\norganizations. Journal of Business Ethics, 9 (3), 233–242.\nStevens, Betsy. (2008). Corporate ethical codes: Effective instruments\nfor inﬂuencing behavior. Journal of Business Ethics, 78 (4),\n601–609.\nStrack, F., & Deutsch, R. (2004). Reﬂective and impulsive determi-\nnants of social behavior. Personality and Social Psychological\nReview, 8 , 220–247.\nStreet, M. D., Douglas, S. C., Geiger, S. W., & Martinko, M. J.\n(2001). The impact of cognitive expenditure on the ethical\ndecision-making process: The cognitive elaboration model.\nOrganizational Behavior and Human Decision Processes,\n86(2), 256–277.\nSykes, G., & Matza, D. (1957). Techniques of neutralization: A\ntheory of delinquency. American Sociological Review, 22 ,\n664–670.\nTangney, J. P., Stuewig, J., & Mashek, D. J. (2007). Moral emotions\nand moral behavior. Annual Review of Psychology, 58 , 345–372.\nTenbrunsel, A. E., & Messick, D. M. (2004). Ethical fading: The role\nof self-deception in unethical behavior. Social Justice Research,\n17(2), 223–236.\nTenbrunsel, A. E., & Smith-Crowe, K. (2008). Ethical decision\nmaking: Where we’ve been and where we’re going. Academy of\nManagement Annals, 2 (1), 545–607.\nTenbrunsel, A. E., Smith-Crowe, K., & Umphress, E. (2003).\nBuilding houses on rocks: The role of the ethical infrastructure\nin organizations. Social Justice Research, 16 (3), 285–307.\nTofﬂer, B. (1986). Tough choices: Managers talk ethics . New York:\nWiley.\nTorres, M. B. (2001). Character and decision making . Unpublished\nDissertation, University of Navarra.\nTrevin˜o, L. K. (1986). Ethical decision making in organizations: A\nperson-situation interactionist model. Academy of Management\nReview, 11 (3), 601–617.\nTrevin˜o, L. K., Butterﬁeld, K. D., & McCabe, D. L. (1998). The\nethical context in organizations: Inﬂuences on employee atti-\ntudes and behaviors. Business Ethics Quarterly, 8 , 447–476.\nTrevin˜o, L. K., Weaver, G. R., & Reynolds, S. J. (2006). Behavioral\nethics in organizations. Journal of Management, 32 (6), 951–990.\nTsang, J. A. (2002). Moral rationalization and the integration of\nsituational factors and psychological processes in immoral\nbehavior. Review of General Psychology, 6 (1), 25–50.\nU.S. Sentencing Commission (2014). Organizations receiving ﬁnes or\nrestitution. Sourcebook for Federal Sentencing Statistics. www.\nussc.gov/research-and-publications/annual-reports-sourcebooks/\n2014/sourcebook-2014.\nValentine, S., & Hollingworth, D. (2012). Moral intensity, issue\nimportance, and ethical reasoning in operations situations.\nJournal of Business Ethics, 108 , 509–523.\nValentine, S., Nam, S. H., Hollingworth, D., & Hall, C. (2013).\nEthical context and ethical decision making: Examination of an\nalternative statistical approach for identifying variable relation-\nships. Journal of Business Ethics, 68 , 1–18.\nVictor, B., & Cullen, J. B. (1988). The organizational bases of ethical\nwork climates. Administrative Science Quarterly, 33 (1),\n101–125.\nEthical Decision-Making Theory: An Integrated Approach 775\n123	paragraph	21	112407	119494	\N	0	1030	7087	288	en	\N	\N	\N	f	\N	\N	\N	\N	\N	2025-08-27 20:36:49.63029	2025-08-27 20:36:49.630291	\N	59
2331	Warren, D. E., & Smith-Crowe, K. (2008). Deciding what’s right: The\nrole of external sanctions and embarrassment in shaping moral\njudgments in the workplace. Research in Organizational\nBehavior, 28 , 81–105.\nWatson, G. W., Berkley, R. A., & Papamarcos, S. D. (2009).\nAmbiguous allure: The value-pragmatics model of ethical\ndecision making. Business and Society Review, 114 (1), 1–29.\nWeaver, G. R., Trevin ˜o, L. K., & Cochran, P. L. (1999). Corporate\nethics practices in the mid-1990’s: An empirical study of the\nFortune 1000. Journal of Business Ethics, 18 (3), 283–294.\nWeber, J. (1993). Exploring the relationship between personal values\nand moral reasoning. Human Relations, 46 (4), 435–463.\nWeber, J. (1996). Inﬂuences upon managerial moral decision-making:\nNature of the harm and magnitude of consequences. Human\nRelations, 49 (1), 1–22.\nWebley, S. (2011). Corporate ethics policies and programmes: UK\nand Continental Europe survey 2010 . London: UK, Institute of\nBusiness Ethics.\nWerhane, P. H. (1998). Moral imagination and the search for ethical\ndecision-making in management. Business Ethics Quarterly,\nRufﬁn Series, 1 , 75–98.\nWhittier, N. C., Williams, S., & Dewett, T. C. (2006). Evaluating\nethical decision-making models: A review and application.\nSociety and Business Review, 1 (3), 235–247.\nWoiceshyn, J. (2011). A model for ethical decision making in\nbusiness: reasoning, intuition, and rational moral principles.\nJournal of Business Ethics, 104 , 311–323.\nWright, J. C. (2005). The role of reasoning and intuition in moral\njudgment: A review . Unpublished PhD Comprehensive Exam,\nUniversity of Wyoming.\nYu, Y. M. (2015). Comparative analysis of Jones’ and Kelley’s\nethical decision-making models. Journal of Business Ethics , 130,\n573–583.\n776 M. S. Schwartz\n123	paragraph	22	119496	121277	\N	0	268	1781	66	en	\N	\N	\N	f	\N	\N	\N	\N	\N	2025-08-27 20:36:49.630293	2025-08-27 20:36:49.630294	\N	59
2332	Reproduced with permission of the copyright owner. Further reproduction prohibited without\npermission.	paragraph	23	121279	121381	\N	0	12	102	2	en	\N	\N	\N	f	\N	\N	\N	\N	\N	2025-08-27 20:36:49.630295	2025-08-27 20:36:49.630296	\N	59
2333	Reproduced with permission of the copyright owner.  Further reproduction prohibited without permission.\nCYNTHIA OZICK'S RABBINICAL APPROACH TO LITERATURE\nRothstein, Mervyn\nNew York Times; Mar 25, 1987; ProQuest One Academic\npg. C.24	paragraph	1	0	232	\N	0	31	232	5	en	\N	\N	\N	f	\N	\N	\N	\N	\N	2025-08-27 20:37:44.153831	2025-08-27 20:37:44.153834	\N	60
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, username, email, password_hash, first_name, last_name, organization, is_active, is_admin, created_at, updated_at, last_login) FROM stdin;
2	test_user	test@example.com	scrypt:32768:8:1$7co0CsFaL4Ci2PCP$dbfb3c2a20be1aa55e7802d17fdc3ca43ae8fbf01b1602c3fc1a1a8f76106a38a34f945ea282d3b8e1f6fbfc30348a923141a097f9087c961bdf9595466590e9	\N	\N	\N	t	f	2025-08-11 14:05:08.556545	2025-08-11 14:05:08.55655	\N
3	wook	wook@admin.local	scrypt:32768:8:1$TyCbt0YoZdyh6QjK$8651d05519b7732a13c23a115d1c660bf6e8d9b54565e81309f9263b7df5336956abb457801c820bbf9c79bb682ba1a9ee0267bf22d657c356e84ac867d92df6	Wook	Admin	\N	t	t	2025-08-20 09:18:26.897552	2025-08-23 21:26:13.020418	2025-08-20 09:22:56.630383
1	chris	chris@example.com	scrypt:32768:8:1$5ddzASQg1QEDwpAd$e33b4b605c3483beb213c4e1ba292cf3a88da93223adc390c79b71b90219c313eb2dd0149951cdafd489c13f406ee2b068b6464878893a61b7a1d1c3f01e3053	\N	\N	\N	t	t	2025-08-11 04:55:29.584732	2025-08-27 12:48:40.870755	2025-08-27 12:48:40.869691
\.


--
-- Name: documents_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.documents_id_seq', 61, true);


--
-- Name: domains_id_seq; Type: SEQUENCE SET; Schema: public; Owner: ontextract_user
--

SELECT pg_catalog.setval('public.domains_id_seq', 1, false);


--
-- Name: experiments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.experiments_id_seq', 27, true);


--
-- Name: extracted_entities_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.extracted_entities_id_seq', 1, false);


--
-- Name: ontologies_id_seq; Type: SEQUENCE SET; Schema: public; Owner: ontextract_user
--

SELECT pg_catalog.setval('public.ontologies_id_seq', 1, false);


--
-- Name: ontology_entities_id_seq; Type: SEQUENCE SET; Schema: public; Owner: ontextract_user
--

SELECT pg_catalog.setval('public.ontology_entities_id_seq', 1, false);


--
-- Name: ontology_mappings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.ontology_mappings_id_seq', 1, false);


--
-- Name: ontology_versions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: ontextract_user
--

SELECT pg_catalog.setval('public.ontology_versions_id_seq', 1, false);


--
-- Name: processing_jobs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.processing_jobs_id_seq', 7, true);


--
-- Name: search_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: ontextract_user
--

SELECT pg_catalog.setval('public.search_history_id_seq', 1, false);


--
-- Name: text_segments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.text_segments_id_seq', 2333, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 3, true);


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

\unrestrict yrZzcVew8KrnIM6lSLpaDnpW7WkrIsCAUPFWvMShZoZ469YhB44fcnvxKrTKPng

