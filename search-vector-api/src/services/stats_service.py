"""Statistics service for retrieving file processing metrics.

This service module provides functionality to retrieve processing statistics
by joining the processing_logs table with the projects table to provide
comprehensive information about document processing status by project.

The service returns aggregated statistics including:
1. Total number of files processed per project
2. Number of successful processing operations per project  
3. Number of failed processing operations per project
4. Number of skipped processing operations per project
5. Overall success rate (successful files / total files, including skipped)
6. Processing success rate (successful files / processed files, excluding skipped)
7. Project metadata (project_id, project_name)
"""

import logging
import psycopg
from typing import List, Dict, Any
from flask import current_app


class StatsService:
    """Statistics service for document processing metrics.
    
    This service class provides functionality to retrieve and aggregate
    document processing statistics from the processing_logs and projects tables.
    It returns comprehensive metrics about file processing success/failure/skipped rates
    organized by project.
    """

    @classmethod
    def get_processing_stats(cls, project_ids: List[str] = None) -> Dict[str, Any]:
        """Retrieve processing statistics aggregated by project.
        
        This method queries the processing_logs table and joins with the projects
        table to provide comprehensive processing statistics. It aggregates the
        data to show total files processed, successful operations, failed
        operations, and skipped operations for each project.
        
        Args:
            project_ids (List[str], optional): List of project IDs to filter results.
                                             If None or empty, returns stats for all projects.
                                             
        Returns:
            dict: A structured response containing processing statistics:
                {
                    "processing_stats": {
                        "projects": [
                            {
                                "project_id": "uuid-string",
                                "project_name": "Project Name",
                                "total_files": 150,
                                "successful_files": 140,
                                "failed_files": 8,
                                "skipped_files": 2,
                                "overall_success_rate": 93.33,
                                "processing_success_rate": 94.59
                            },
                            ...
                        ],
                        "summary": {
                            "total_projects": 5,
                            "total_files_across_all_projects": 750,
                            "total_successful_files": 720,
                            "total_failed_files": 25,
                            "total_skipped_files": 5,
                            "overall_success_rate": 96.0,
                            "overall_processing_success_rate": 96.64
                        }
                    }
                }
                
        Examples:
            Get stats for all projects:
            >>> StatsService.get_processing_stats()
            
            Get stats for specific projects:
            >>> StatsService.get_processing_stats(["proj-001", "proj-002"])
        """
        
        try:
            # Build the WHERE clause for project filtering
            where_conditions = []
            params = []
            
            if project_ids and len(project_ids) > 0:
                placeholders = ','.join(['%s'] * len(project_ids))
                where_conditions.append(f"p.project_id IN ({placeholders})")
                params.extend(project_ids)
                
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            # SQL query to get processing statistics by project
            stats_query = f"""
            SELECT 
                p.project_id,
                p.project_name,
                COUNT(pl.*) as total_files,
                COUNT(CASE WHEN pl.status = 'success' THEN 1 END) as successful_files,
                COUNT(CASE WHEN pl.status = 'failure' THEN 1 END) as failed_files,
                COUNT(CASE WHEN pl.status = 'skipped' THEN 1 END) as skipped_files,
                CASE 
                    WHEN COUNT(pl.*) > 0 THEN 
                        ROUND((COUNT(CASE WHEN pl.status = 'success' THEN 1 END) * 100.0 / COUNT(pl.*)), 2)
                    ELSE 0 
                END as success_rate,
                CASE 
                    WHEN (COUNT(CASE WHEN pl.status = 'success' THEN 1 END) + COUNT(CASE WHEN pl.status = 'failure' THEN 1 END)) > 0 THEN 
                        ROUND((COUNT(CASE WHEN pl.status = 'success' THEN 1 END) * 100.0 / (COUNT(CASE WHEN pl.status = 'success' THEN 1 END) + COUNT(CASE WHEN pl.status = 'failure' THEN 1 END))), 2)
                    ELSE 0 
                END as processed_success_rate
            FROM projects p
            LEFT JOIN processing_logs pl ON p.project_id = pl.project_id
            {where_clause}
            GROUP BY p.project_id, p.project_name
            ORDER BY p.project_name;
            """
            
            logging.info(f"Executing stats query with params: {params}")
            
            # Execute the query
            conn_params = current_app.vector_settings.database_url
            with psycopg.connect(conn_params) as conn:
                with conn.cursor() as cur:
                    cur.execute(stats_query, params)
                    results = cur.fetchall()
            
            # Process the results
            projects_stats = []
            total_projects = 0
            total_files_all = 0
            total_successful_all = 0
            total_failed_all = 0
            total_skipped_all = 0
            
            for row in results:
                project_id, project_name, total_files, successful_files, failed_files, skipped_files, success_rate, processed_success_rate = row
                
                # Only include projects that have processing logs
                if total_files > 0:
                    projects_stats.append({
                        "project_id": project_id,
                        "project_name": project_name,
                        "total_files": total_files,
                        "successful_files": successful_files,
                        "failed_files": failed_files,
                        "skipped_files": skipped_files,
                        "overall_success_rate": float(success_rate) if success_rate else 0.0,
                        "processing_success_rate": float(processed_success_rate) if processed_success_rate else 0.0
                    })
                    
                    total_projects += 1
                    total_files_all += total_files
                    total_successful_all += successful_files
                    total_failed_all += failed_files
                    total_skipped_all += skipped_files
            
            # Calculate overall success rate
            overall_success_rate = (
                round((total_successful_all * 100.0 / total_files_all), 2) 
                if total_files_all > 0 else 0.0
            )
            
            # Calculate overall processed success rate (successful vs processed, excluding skipped)
            total_processed_all = total_successful_all + total_failed_all
            overall_processing_success_rate = (
                round((total_successful_all * 100.0 / total_processed_all), 2) 
                if total_processed_all > 0 else 0.0
            )
            
            response = {
                "processing_stats": {
                    "projects": projects_stats,
                    "summary": {
                        "total_projects": total_projects,
                        "total_files_across_all_projects": total_files_all,
                        "total_successful_files": total_successful_all,
                        "total_failed_files": total_failed_all,
                        "total_skipped_files": total_skipped_all,
                        "overall_success_rate": overall_success_rate,
                        "overall_processing_success_rate": overall_processing_success_rate
                    }
                }
            }
            
            logging.info(f"Retrieved stats for {total_projects} projects with {total_files_all} total files")
            return response
            
        except Exception as e:
            logging.error(f"Error retrieving processing stats: {e}")
            # Return empty stats on error
            return {
                "processing_stats": {
                    "projects": [],
                    "summary": {
                        "total_projects": 0,
                        "total_files_across_all_projects": 0,
                        "total_successful_files": 0,
                        "total_failed_files": 0,
                        "total_skipped_files": 0,
                        "overall_success_rate": 0.0,
                        "overall_processing_success_rate": 0.0
                    }
                },
                "error": str(e)
            }

    @classmethod
    def get_project_processing_details(cls, project_id: str) -> Dict[str, Any]:
        """Get detailed processing information for a specific project.
        
        This method provides detailed processing logs for a specific project,
        including individual file processing records with timestamps and
        status information.
        
        Args:
            project_id (str): The ID of the project to get detailed stats for.
                              
        Returns:
            dict: Detailed processing information for the project:
                {
                    "project_details": {
                        "project_id": "uuid-string",
                        "project_name": "Project Name",
                        "processing_logs": [
                            {
                                "log_id": "log-uuid",
                                "document_id": "document.pdf",
                                "status": "success",
                                "processed_at": "2024-01-15T10:30:00Z",
                                "metrics": null
                            },
                            ...
                        ],
                        "summary": {
                            "total_files": 50,
                            "successful_files": 46,
                            "failed_files": 2,
                            "skipped_files": 2,
                            "overall_success_rate": 92.0,
                            "processing_success_rate": 95.83
                        }
                    }
                }
        """
        
        try:
            # SQL query to get detailed processing logs for a specific project
            details_query = """
            SELECT 
                p.project_id,
                p.project_name,
                pl.id as log_id,
                pl.document_id,
                pl.status,
                pl.processed_at,
                pl.metrics
            FROM projects p
            LEFT JOIN processing_logs pl ON p.project_id = pl.project_id
            WHERE p.project_id = %s
            ORDER BY pl.processed_at DESC;
            """
            
            logging.info(f"Getting detailed stats for project: {project_id}")
            
            # Execute the query
            conn_params = current_app.vector_settings.database_url
            with psycopg.connect(conn_params) as conn:
                with conn.cursor() as cur:
                    cur.execute(details_query, [project_id])
                    results = cur.fetchall()
            
            if not results:
                return {
                    "project_details": None,
                    "error": f"Project {project_id} not found"
                }
            
            # Process the results
            project_id_result = results[0][0]
            project_name = results[0][1]
            
            processing_logs = []
            total_files = 0
            successful_files = 0
            failed_files = 0
            skipped_files = 0
            
            for row in results:
                _, _, log_id, document_id, status, processed_at, metrics = row
                
                # Skip rows where there's no processing log (only project info)
                if log_id is not None:
                    processing_logs.append({
                        "log_id": log_id,
                        "document_id": document_id,
                        "status": status,
                        "processed_at": processed_at.isoformat() if processed_at else None,
                        "metrics": metrics
                    })
                    
                    total_files += 1
                    if status == 'success':
                        successful_files += 1
                    elif status == 'failure':
                        failed_files += 1
                    elif status == 'skipped':
                        skipped_files += 1
            
            overall_success_rate = (
                round((successful_files * 100.0 / total_files), 2) 
                if total_files > 0 else 0.0
            )
            
            # Calculate processed success rate (successful vs processed, excluding skipped)
            total_processed = successful_files + failed_files
            processing_success_rate = (
                round((successful_files * 100.0 / total_processed), 2) 
                if total_processed > 0 else 0.0
            )
            
            response = {
                "project_details": {
                    "project_id": project_id_result,
                    "project_name": project_name,
                    "processing_logs": processing_logs,
                    "summary": {
                        "total_files": total_files,
                        "successful_files": successful_files,
                        "failed_files": failed_files,
                        "skipped_files": skipped_files,
                        "overall_success_rate": overall_success_rate,
                        "processing_success_rate": processing_success_rate
                    }
                }
            }
            
            logging.info(f"Retrieved detailed stats for project {project_id}: {total_files} files")
            return response
            
        except Exception as e:
            logging.error(f"Error retrieving detailed stats for project {project_id}: {e}")
            return {
                "project_details": None,
                "error": str(e)
            }
