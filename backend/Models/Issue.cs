using System;
using System.Collections.Generic;

namespace backend.Models;

public partial class Issue
{
    public int Issueid { get; set; }

    public string Text { get; set; } = null!;

    public int Suggestionid { get; set; }

    public virtual ICollection<Review> Reviews { get; set; } = new List<Review>();

    public virtual Suggestion Suggestion { get; set; } = null!;
}
