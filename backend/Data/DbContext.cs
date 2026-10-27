using System;
using System.Collections.Generic;
using Microsoft.EntityFrameworkCore;
using backend.Models;

namespace backend.Data;

public partial class DbContext : DbContext
{
    public DbContext()
    {
    }

    public DbContext(DbContextOptions<DbContext> options)
        : base(options)
    {
    }

    public virtual DbSet<Analysis> Analyses { get; set; }

    public virtual DbSet<Issue> Issues { get; set; }

    public virtual DbSet<Package> Packages { get; set; }

    public virtual DbSet<Resource> Resources { get; set; }

    public virtual DbSet<Review> Reviews { get; set; }

    public virtual DbSet<Suggestion> Suggestions { get; set; }

    protected override void OnConfiguring(DbContextOptionsBuilder optionsBuilder)
        => optionsBuilder.UseNpgsql("Host=localhost;Port=5433;Database=;Username=;Password=");

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Analysis>(entity =>
        {
            entity.HasKey(e => e.Analysisid).HasName("analysis_pkey");

            entity.ToTable("analysis");

            entity.Property(e => e.Analysisid)
                .ValueGeneratedNever()
                .HasColumnName("analysisid");
            entity.Property(e => e.Datetime)
                .HasColumnType("timestamp without time zone")
                .HasColumnName("datetime");
            entity.Property(e => e.Idnext).HasColumnName("idnext");
            entity.Property(e => e.Idprev).HasColumnName("idprev");

            entity.HasIndex(e => e.Idnext, "analysis_idnext_key").IsUnique();
            entity.HasIndex(e => e.Idprev, "analysis_idprev_key").IsUnique();

            entity.HasOne(d => d.NextAnalysis)
                .WithOne()
                .HasForeignKey<Analysis>(d => d.Idnext)
                .HasConstraintName("analysis_idnext_fkey");

            entity.HasOne(d => d.PreviousAnalysis)
                .WithOne()
                .HasForeignKey<Analysis>(d => d.Idprev)
                .HasConstraintName("analysis_idprev_fkey");
        });

        modelBuilder.Entity<Issue>(entity =>
        {
            entity.HasKey(e => e.Issueid).HasName("issue_pkey");

            entity.ToTable("issue");

            entity.Property(e => e.Issueid)
                .ValueGeneratedNever()
                .HasColumnName("issueid");
            entity.Property(e => e.Suggestionid).HasColumnName("suggestionid");
            entity.Property(e => e.Text)
                .HasMaxLength(255)
                .HasColumnName("text");

            entity.HasOne(d => d.Suggestion).WithMany(p => p.Issues)
                .HasForeignKey(d => d.Suggestionid)
                .OnDelete(DeleteBehavior.ClientSetNull)
                .HasConstraintName("issue_suggestionid_fkey");
        });

        modelBuilder.Entity<Package>(entity =>
        {
            entity.HasKey(e => e.Packageid).HasName("package_pkey");

            entity.ToTable("package");

            entity.Property(e => e.Packageid)
                .HasMaxLength(100)
                .HasColumnName("packageid");
            entity.Property(e => e.Description)
                .HasMaxLength(1000)
                .HasColumnName("description");
            entity.Property(e => e.Title)
                .HasMaxLength(100)
                .HasColumnName("title");
            entity.Property(e => e.Url)
                .HasMaxLength(1000)
                .HasColumnName("url");
        });

        modelBuilder.Entity<Resource>(entity =>
        {
            entity.HasKey(e => e.Resourceid).HasName("resource_pkey");

            entity.ToTable("resource");

            entity.Property(e => e.Resourceid)
                .HasMaxLength(100)
                .HasColumnName("resourceid");
            entity.Property(e => e.Format)
                .HasMaxLength(50)
                .HasColumnName("format");
            entity.Property(e => e.Packageid)
                .HasMaxLength(100)
                .HasColumnName("packageid");
            entity.Property(e => e.Url)
                .HasMaxLength(1000)
                .HasColumnName("url");

            entity.HasOne(d => d.Package).WithMany(p => p.Resources)
                .HasForeignKey(d => d.Packageid)
                .OnDelete(DeleteBehavior.ClientSetNull)
                .HasConstraintName("resource_packageid_fkey");
        });

        modelBuilder.Entity<Review>(entity =>
        {
            entity.HasKey(e => new { e.Issueid, e.Analysisid }).HasName("review_pkey");

            entity.ToTable("review");

            entity.Property(e => e.Issueid).HasColumnName("issueid");
            entity.Property(e => e.Analysisid).HasColumnName("analysisid");
            entity.Property(e => e.Status).HasColumnName("status");

            entity.HasOne(d => d.Analysis).WithMany(p => p.Reviews)
                .HasForeignKey(d => d.Analysisid)
                .OnDelete(DeleteBehavior.ClientSetNull)
                .HasConstraintName("review_analysisid_fkey");

            entity.HasOne(d => d.Issue).WithMany(p => p.Reviews)
                .HasForeignKey(d => d.Issueid)
                .OnDelete(DeleteBehavior.ClientSetNull)
                .HasConstraintName("review_issueid_fkey");
        });

        modelBuilder.Entity<Suggestion>(entity =>
        {
            entity.HasKey(e => e.Suggestionid).HasName("suggestion_pkey");

            entity.ToTable("suggestion");

            entity.Property(e => e.Suggestionid)
                .ValueGeneratedNever()
                .HasColumnName("suggestionid");
            entity.Property(e => e.Datetime)
                .HasColumnType("timestamp without time zone")
                .HasColumnName("datetime");
            entity.Property(e => e.Packageid)
                .HasMaxLength(100)
                .HasColumnName("packageid");
            entity.Property(e => e.Text)
                .HasMaxLength(1000)
                .HasColumnName("text");
            entity.Property(e => e.Title)
                .HasMaxLength(100)
                .HasColumnName("title");

            entity.HasOne(d => d.Package).WithMany(p => p.Suggestions)
                .HasForeignKey(d => d.Packageid)
                .OnDelete(DeleteBehavior.ClientSetNull)
                .HasConstraintName("suggestion_packageid_fkey");
        });

        OnModelCreatingPartial(modelBuilder);
    }

    partial void OnModelCreatingPartial(ModelBuilder modelBuilder);
}
