"""
CLI commands for vector database operations
"""

import typer
from pathlib import Path
from typing import Optional
import json
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from rich.panel import Panel

from ..data_loader import HousingDataLoader
from ..client import VectorDBClient
from ..embeddings.korean import KoreanEmbedder
from ..collections.housing import HousingCollection

app = typer.Typer(help="Vector Database CLI for housing data")
console = Console()


@app.command()
def load_data(
    csv_path: Optional[Path] = typer.Option(
        None, 
        "--csv-path", 
        "-c", 
        help="Path to housing CSV file"
    ),
    batch_size: int = typer.Option(
        32, 
        "--batch-size", 
        "-b", 
        help="Batch size for processing"
    ),
    clear_existing: bool = typer.Option(
        False, 
        "--clear", 
        help="Clear existing data before loading"
    )
):
    """Load housing data from CSV to vector database"""
    
    console.print("[bold blue]Loading housing data to vector database...[/bold blue]")
    
    try:
        # Initialize loader
        loader = HousingDataLoader(csv_path=csv_path)
        
        # Load data
        loader.load_to_vector_db(
            batch_size=batch_size,
            clear_existing=clear_existing
        )
        
        console.print("[bold green]✓ Successfully loaded housing data![/bold green]")
        
        # Show statistics
        stats = loader.get_loading_statistics()
        console.print(f"[green]Total records loaded: {stats['total_count']}[/green]")
        
    except Exception as e:
        console.print(f"[bold red]✗ Failed to load data: {e}[/bold red]")
        raise typer.Exit(1)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    n_results: int = typer.Option(10, "--limit", "-n", help="Number of results"),
    district: Optional[str] = typer.Option(None, "--district", "-d", help="Filter by district"),
    dong: Optional[str] = typer.Option(None, "--dong", help="Filter by dong"),
    theme: Optional[str] = typer.Option(None, "--theme", "-t", help="Filter by theme"),
    min_similarity: float = typer.Option(0.0, "--min-sim", help="Minimum similarity threshold"),
    hybrid: bool = typer.Option(False, "--hybrid", help="Use hybrid keyword+vector search")
):
    """Search for similar housing"""
    
    search_type = "Hybrid" if hybrid else "Vector"
    console.print(f"[bold blue]{search_type} Searching for: '{query}'[/bold blue]")
    
    try:
        # Initialize components
        client = VectorDBClient()
        embedder = KoreanEmbedder()
        collection = HousingCollection(client, embedder)
        
        # Connect and load model
        client.connect()
        embedder.load_model()
        
        # Perform search
        if hybrid:
            results = collection.search_by_keyword(
                query=query,
                min_similarity=min_similarity if min_similarity > 0 else 0.2,
                n_results=n_results
            )
        elif district or dong:
            results = collection.search_by_location(
                query=query,
                district=district,
                dong=dong,
                n_results=n_results
            )
        elif theme:
            results = collection.search_by_theme(
                query=query,
                theme_keywords=[theme],
                n_results=n_results
            )
        else:
            results = collection.search_similar(
                query=query,
                n_results=n_results
            )
        
        # Filter by minimum similarity if specified
        if min_similarity > 0 and not hybrid:
            results = [r for r in results if r['similarity'] >= min_similarity]
        
        # Display results
        if not results:
            console.print("[yellow]No results found[/yellow]")
            if min_similarity > 0:
                console.print(f"[yellow]Try lowering --min-sim threshold (current: {min_similarity})[/yellow]")
            return
        
        # Create results table
        table = Table(title=f"{search_type} Search Results for '{query}'")
        table.add_column("Rank", style="cyan", width=4)
        table.add_column("Housing Name", style="green", width=25)
        table.add_column("Location", style="blue", width=30)
        table.add_column("Similarity", style="magenta", width=10)
        table.add_column("Theme", style="yellow", width=20)
        
        for i, result in enumerate(results, 1):
            metadata = result['metadata']
            similarity = f"{result['similarity']:.3f}"
            
            # Color code similarity
            if result['similarity'] >= 0.5:
                similarity_color = "green"
            elif result['similarity'] >= 0.3:
                similarity_color = "yellow"
            else:
                similarity_color = "red"
            
            theme = metadata.get('theme', '')[:18] + "..." if len(metadata.get('theme', '')) > 18 else metadata.get('theme', '')
            
            table.add_row(
                str(i),
                metadata.get('주택명', '')[:23],
                f"{metadata.get('시군구', '')} {metadata.get('동명', '')}",
                f"[{similarity_color}]{similarity}[/{similarity_color}]",
                theme
            )
        
        console.print(table)
        
        # Show statistics
        avg_similarity = sum(r['similarity'] for r in results) / len(results)
        console.print(f"\n[blue]Average similarity: {avg_similarity:.3f}[/blue]")
        
        if hybrid:
            console.print("[green]💡 Used hybrid keyword+vector search[/green]")
        
    except Exception as e:
        console.print(f"[bold red]✗ Search failed: {e}[/bold red]")
        raise typer.Exit(1)
    finally:
        client.disconnect()


@app.command()
def stats():
    """Show vector database statistics"""
    
    console.print("[bold blue]Vector Database Statistics[/bold blue]")
    
    try:
        loader = HousingDataLoader()
        stats = loader.get_loading_statistics()
        
        # Total count
        console.print(f"\n[green]Total Housing Records: {stats['total_count']}[/green]")
        
        # Districts
        if stats.get('districts'):
            console.print("\n[bold]Top Districts:[/bold]")
            district_table = Table()
            district_table.add_column("District", style="cyan")
            district_table.add_column("Count", style="green")
            
            for district, count in list(stats['districts'].items())[:10]:
                district_table.add_row(district, str(count))
            
            console.print(district_table)
        
        # Themes
        if stats.get('themes'):
            console.print("\n[bold]Top Themes:[/bold]")
            theme_table = Table()
            theme_table.add_column("Theme", style="cyan")
            theme_table.add_column("Count", style="green")
            
            for theme, count in list(stats['themes'].items())[:10]:
                theme_table.add_row(theme, str(count))
            
            console.print(theme_table)
        
        # Database info
        if stats.get('database_info'):
            db_info = stats['database_info']
            console.print(f"\n[blue]Database Path: {db_info['persist_directory']}[/blue]")
            console.print(f"[blue]Collections: {db_info['total_collections']}[/blue]")
        
    except Exception as e:
        console.print(f"[bold red]✗ Failed to get statistics: {e}[/bold red]")
        raise typer.Exit(1)


@app.command()
def preview(
    n_samples: int = typer.Option(3, "--samples", "-n", help="Number of samples to preview")
):
    """Preview embeddings for sample data"""
    
    console.print("[bold blue]Previewing embeddings...[/bold blue]")
    
    try:
        loader = HousingDataLoader()
        previews = loader.preview_embeddings(n_samples=n_samples)
        
        for i, preview in enumerate(previews, 1):
            panel_content = f"""
[bold]Housing Name:[/bold] {preview['housing_name']}

[bold]Text Representation:[/bold]
{preview['text_representation']}

[bold]Embedding Info:[/bold]
- Dimension: {preview['embedding_dimension']}
- Sample values: {preview['embedding_sample']}
            """
            
            console.print(Panel(
                panel_content.strip(),
                title=f"Sample {i}",
                border_style="blue"
            ))
        
    except Exception as e:
        console.print(f"[bold red]✗ Preview failed: {e}[/bold red]")
        raise typer.Exit(1)


@app.command()
def inspect(
    housing_id: Optional[str] = typer.Option(None, "--id", help="Specific housing ID to inspect"),
    show_full_embedding: bool = typer.Option(False, "--full-embedding", help="Show full embedding vector"),
    n_random: int = typer.Option(0, "--random", "-r", help="Show N random documents")
):
    """Inspect detailed data in vector database"""
    
    console.print("[bold blue]Inspecting vector database data...[/bold blue]")
    
    try:
        # Initialize components
        client = VectorDBClient()
        embedder = KoreanEmbedder()
        collection = HousingCollection(client, embedder)
        
        client.connect()
        
        if housing_id:
            # Show specific document
            doc = collection.get_document(housing_id)
            if doc:
                _display_document_details(doc, show_full_embedding)
            else:
                console.print(f"[red]Document with ID '{housing_id}' not found[/red]")
                
        elif n_random > 0:
            # Show random documents
            # Get all documents and sample randomly
            chroma_collection = collection._get_collection()
            all_results = chroma_collection.get(
                include=['metadatas', 'documents', 'embeddings' if show_full_embedding else 'metadatas']
            )
            
            if not all_results['ids']:
                console.print("[yellow]No documents found in database[/yellow]")
                return
            
            import random
            indices = random.sample(range(len(all_results['ids'])), min(n_random, len(all_results['ids'])))
            
            for i, idx in enumerate(indices, 1):
                console.print(f"\n[bold cyan]Random Document {i}:[/bold cyan]")
                
                doc_data = {
                    'id': all_results['ids'][idx],
                    'document': all_results['documents'][idx],
                    'metadata': all_results['metadatas'][idx]
                }
                
                if show_full_embedding and 'embeddings' in all_results:
                    doc_data['embedding'] = all_results['embeddings'][idx]
                
                _display_document_details(doc_data, show_full_embedding)
        else:
            # Show database overview
            console.print("[yellow]Use --id to inspect specific document or --random N to see random samples[/yellow]")
            
            # Show basic stats
            count = collection.count()
            console.print(f"[green]Total documents in database: {count}[/green]")
            
            if count > 0:
                console.print("\n[blue]Sample usage:[/blue]")
                console.print("  vector-db inspect --random 3")
                console.print("  vector-db inspect --id <document_id>")
        
    except Exception as e:
        console.print(f"[bold red]✗ Inspection failed: {e}[/bold red]")
        raise typer.Exit(1)
    finally:
        client.disconnect()


def _display_document_details(doc_data: dict, show_full_embedding: bool = False):
    """Display detailed document information"""
    
    # Basic info
    console.print(f"[bold]Document ID:[/bold] {doc_data['id']}")
    console.print(f"[bold]Document Text:[/bold]")
    console.print(doc_data['document'])
    
    # Metadata
    console.print(f"\n[bold]Metadata:[/bold]")
    metadata = doc_data['metadata']
    
    # Create metadata table
    meta_table = Table(show_header=False, box=None)
    meta_table.add_column("Key", style="cyan", width=15)
    meta_table.add_column("Value", style="white")
    
    for key, value in metadata.items():
        if value:  # Only show non-empty values
            meta_table.add_row(key, str(value)[:50] + "..." if len(str(value)) > 50 else str(value))
    
    console.print(meta_table)
    
    # Embedding info
    if 'embedding' in doc_data and show_full_embedding:
        embedding = doc_data['embedding']
        console.print(f"\n[bold]Full Embedding Vector:[/bold]")
        console.print(f"Dimension: {len(embedding)}")
        
        # Show embedding in chunks of 10
        for i in range(0, len(embedding), 10):
            chunk = embedding[i:i+10]
            formatted_chunk = [f"{val:.4f}" for val in chunk]
            console.print(f"[{i:3d}-{min(i+9, len(embedding)-1):3d}]: {formatted_chunk}")
    
    elif 'embedding' in doc_data:
        embedding = doc_data['embedding']
        console.print(f"\n[bold]Embedding Info:[/bold]")
        console.print(f"Dimension: {len(embedding)}")
        console.print(f"Sample (first 10): {[f'{val:.4f}' for val in embedding[:10]]}")
    
    console.print("\n" + "─" * 60)


@app.command()
def clear():
    """Clear all data from vector database"""
    
    confirm = typer.confirm("Are you sure you want to clear all vector database data?")
    if not confirm:
        console.print("[yellow]Operation cancelled[/yellow]")
        return
    
    try:
        client = VectorDBClient()
        client.connect()
        client.reset_database()
        
        console.print("[bold green]✓ Vector database cleared successfully![/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]✗ Failed to clear database: {e}[/bold red]")
        raise typer.Exit(1)
    finally:
        client.disconnect()


@app.command()
def info():
    """Show vector database information"""
    
    try:
        client = VectorDBClient()
        client.connect()
        
        db_info = client.get_database_info()
        
        console.print("[bold blue]Vector Database Information[/bold blue]")
        console.print(f"\n[green]Database Path:[/green] {db_info['persist_directory']}")
        console.print(f"[green]Total Collections:[/green] {db_info['total_collections']}")
        
        if db_info['collections']:
            console.print("\n[bold]Collections:[/bold]")
            
            for col_name in db_info['collections']:
                col_details = db_info['collection_details'].get(col_name, {})
                
                if 'error' in col_details:
                    console.print(f"  • {col_name}: [red]Error - {col_details['error']}[/red]")
                else:
                    count = col_details.get('count', 0)
                    console.print(f"  • {col_name}: [green]{count} documents[/green]")
        else:
            console.print("\n[yellow]No collections found[/yellow]")
        
    except Exception as e:
        console.print(f"[bold red]✗ Failed to get database info: {e}[/bold red]")
        raise typer.Exit(1)
    finally:
        client.disconnect()


if __name__ == "__main__":
    app()
